import { z } from 'zod';
import catalog from '../../contracts/questions.v1.json';

export const questionCatalog = catalog;
export const questionIdSchema = z.enum([
  'event_type', 'urgency', 'owning_agent', 'action_gate',
]);
export type QuestionId = z.infer<typeof questionIdSchema>;
export const identifierSchema = z.string().min(1).regex(/^\S+$/);
const summarySchema = z.string().min(1);
const probabilitySchema = z.number().finite().min(0).max(1);
const nonNegativeIntSchema = z.number().int().nonnegative();
export const executionModeSchema = z.enum(['live', 'mock', 'replay', 'recorded_replay']);
export const policyOutcomeSchema = z.enum(['proceed', 'require_approval', 'block']);
export const humanRoutingStateSchema = z.literal('human');
export type PolicyOutcome = z.infer<typeof policyOutcomeSchema>;
export type HumanRoutingState = z.infer<typeof humanRoutingStateSchema>;
export type ExecutionMode = z.infer<typeof executionModeSchema>;

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
const jsonValueSchema: z.ZodType<JsonValue> = z.lazy(() => z.union([
  z.string(), z.number().finite(), z.boolean(), z.null(),
  z.array(jsonValueSchema), z.record(z.string(), jsonValueSchema),
]));
const jsonObjectSchema = z.record(z.string(), jsonValueSchema);

export const plantEventSchema = z.strictObject({
  eventId: identifierSchema,
  occurredAt: z.iso.datetime({ offset: true }).refine((value) => !value.startsWith('0000-'), {
    message: 'Timestamp year must be between 0001 and 9999',
  }),
  kind: z.enum(['andon', 'supplier_notice', 'inspection', 'maintenance', 'engineering_change']),
  source: identifierSchema,
  summary: summarySchema,
  facts: jsonObjectSchema,
});
export type PlantEvent = z.infer<typeof plantEventSchema>;

export const decisionResultSchema = z.strictObject({
  questionId: questionIdSchema,
  selectedChoice: identifierSchema,
  probabilities: z.record(z.string(), probabilitySchema),
  confidence: probabilitySchema,
  modelId: identifierSchema,
  elapsedMs: z.number().finite().nonnegative(),
  executionMode: executionModeSchema,
}).superRefine((result, ctx) => {
  const choices: readonly string[] = catalog.questions[result.questionId];
  if (!choices.includes(result.selectedChoice)) {
    ctx.addIssue({ code: 'custom', message: 'Unknown selected choice', path: ['selectedChoice'] });
  }
  const keys = Object.keys(result.probabilities);
  if (keys.length !== choices.length || !keys.every((key) => choices.includes(key))) {
    ctx.addIssue({ code: 'custom', message: 'Probabilities must cover exactly the known choices', path: ['probabilities'] });
  }
});
export type DecisionResult = z.infer<typeof decisionResultSchema>;

export const requestUsageSchema = z.strictObject({
  requestId: identifierSchema,
  inputTokens: nonNegativeIntSchema,
  outputTokens: nonNegativeIntSchema,
  totalTokens: nonNegativeIntSchema,
}).refine((usage) => usage.totalTokens === usage.inputTokens + usage.outputTokens, {
  message: 'Token total must equal input plus output',
});
export const decisionResultSetSchema = z.strictObject({
  results: z.partialRecord(questionIdSchema, decisionResultSchema),
  usage: requestUsageSchema,
}).superRefine((set, ctx) => {
  if (Object.keys(set.results).length === 0) {
    ctx.addIssue({ code: 'custom', message: 'At least one decision result is required' });
  }
  for (const [key, result] of Object.entries(set.results)) {
    if (key !== result.questionId) {
      ctx.addIssue({ code: 'custom', message: 'Result key must match questionId', path: ['results', key] });
    }
  }
});
export type DecisionResultSet = z.infer<typeof decisionResultSetSchema>;

export const proposedActionSchema = z.strictObject({
  actionId: identifierSchema,
  eventId: identifierSchema,
  agentId: identifierSchema,
  kind: z.enum(['hold_lot', 'expedite_freight', 'resequence_line', 'open_work_order']),
  summary: summarySchema,
  parameters: jsonObjectSchema,
});
export type ProposedAction = z.infer<typeof proposedActionSchema>;

const envelope = {
  runId: identifierSchema,
  eventId: identifierSchema,
  sequence: nonNegativeIntSchema,
};
const gateSchema = z.enum(['triage', 'action']);
const stepElapsedSchema = z.number().finite().nonnegative().nullable().optional();
export const pacingStateSchema = z.strictObject({
  queuedCount: nonNegativeIntSchema,
  active: z.boolean(),
  requestsInWindow: nonNegativeIntSchema,
  reservedCalls: nonNegativeIntSchema,
  windowSeconds: z.number().finite().positive(),
  windowRequestLimit: z.number().int().positive(),
  remainingRequests: nonNegativeIntSchema,
  windowCompleteEventLimit: z.number().int().positive(),
  completeEventsInWindow: nonNegativeIntSchema,
  pacingState: z.enum(['idle', 'queued', 'running', 'quota_wait', 'throttled']),
  nextAvailableInSeconds: z.number().finite().nonnegative(),
}).refine((state) => state.remainingRequests === Math.max(
  0, state.windowRequestLimit - state.requestsInWindow - state.reservedCalls,
), { message: 'Remaining local capacity must exclude requests and reservations' });
export const demoEventSchema = z.discriminatedUnion('type', [
  z.strictObject({
    ...envelope, type: z.literal('event_received'),
    event: plantEventSchema, executionMode: executionModeSchema,
  }).refine((event) => event.eventId === event.event.eventId, { message: 'Envelope eventId must match event' }),
  z.strictObject({ ...envelope, type: z.literal('gate_started'), gate: gateSchema }),
  z.strictObject({
    ...envelope, type: z.literal('gate_completed'), gate: gateSchema, decisions: decisionResultSetSchema,
    elapsedMs: stepElapsedSchema,
  }),
  z.strictObject({ ...envelope, type: z.literal('agent_selected'), agentId: identifierSchema }),
  z.strictObject({
    ...envelope, type: z.literal('agent_skipped'), routingState: humanRoutingStateSchema, reason: summarySchema,
  }),
  z.strictObject({ ...envelope, type: z.literal('action_proposed'), action: proposedActionSchema, elapsedMs: stepElapsedSchema })
    .refine((event) => event.eventId === event.action.eventId, { message: 'Envelope eventId must match action' }),
  z.strictObject({
    ...envelope, type: z.literal('policy_applied'), actionId: identifierSchema,
    outcome: policyOutcomeSchema, ruleId: identifierSchema, reason: summarySchema,
    elapsedMs: stepElapsedSchema,
  }),
  z.strictObject({ ...envelope, type: z.literal('run_failed'), code: identifierSchema, message: summarySchema }),
  z.strictObject({ ...envelope, type: z.literal('run_completed'), executionMode: executionModeSchema }),
  z.strictObject({ ...envelope, type: z.literal('run_cancelled'), reason: summarySchema }),
  z.strictObject({
    ...envelope, type: z.literal('pacing'),
    deployment: z.enum(['decision-gate', 'specialist-llm']), state: pacingStateSchema,
  }),
]);
export type DemoEvent = z.infer<typeof demoEventSchema>;

export const demoEventStreamSchema = z.array(demoEventSchema).superRefine((events, ctx) => {
  const previous = new Map<string, number>();
  events.forEach((event, index) => {
    const sequence = previous.get(event.runId);
    if (sequence !== undefined && event.sequence <= sequence) {
      ctx.addIssue({ code: 'custom', message: 'Sequence must strictly increase within each run', path: [index, 'sequence'] });
    }
    previous.set(event.runId, event.sequence);
  });
});

export const runRequestSchema = z.strictObject({
  eventId: identifierSchema.optional(),
  mode: z.enum(['replay', 'live', 'mock']).optional(),
});
export type RunRequest = z.infer<typeof runRequestSchema>;
export const runSnapshotSchema = z.strictObject({
  runId: identifierSchema,
  eventId: identifierSchema,
  state: z.enum(['queued', 'running', 'completed', 'cancelled', 'failed']),
  executionMode: z.enum(['live', 'mock', 'recorded_replay']),
  syntheticDataOnly: z.literal(true),
  externalActionsEnabled: z.literal(false),
  historyStartSequence: nonNegativeIntSchema,
  nextSequence: nonNegativeIntSchema,
  history: demoEventStreamSchema,
});
export type RunSnapshot = z.infer<typeof runSnapshotSchema>;

export const liveConfigSchema = z.strictObject({
  enabled: z.boolean(),
  authentication: z.literal('AzureCliCredential'),
  syntheticDataOnly: z.literal(true),
  externalActionsEnabled: z.literal(false),
});

export const healthResponseSchema = z.strictObject({
  status: z.literal('ok'),
  executionMode: z.literal('mock'),
  syntheticDataOnly: z.literal(true),
  externalActionsEnabled: z.literal(false),
});
