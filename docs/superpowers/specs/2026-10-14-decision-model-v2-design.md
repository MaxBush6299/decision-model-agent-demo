# Decision model v2: selective expert team

**Status:** Approved. Original shortage specification `a6036a3` was approved
2026-10-14 and implemented in `ee7d404`. On the same date the user selected a
researched quality-hold/customer-delivery case and approved implementation:
"Lets try this now". This revision supersedes the shortage facts, human field
map and terminal presentation, not the bounded architecture/auth constraints.
No additional conceptual approval gate or live-inference permission is implied.

## User-directed synthetic case

Freeze a Thursday2026-10-15 14:00 UTC-05:00 snapshot. Fictional Tier-2 stamped
mounting brackets to a Tier-1 customer:

- Incident QI-2026-1042, part MB-217, lot L-1042:960 total =720 onsite already
  Quality-held +240 shipped via SH-882 / ASN-019443.
- Measured failures6 of80 checked. Total nonconforming units unknown; no
  extrapolated defect count/rate for the lot.
- Different independently released lot L-1038 has180 usable. Held stock is
  excluded from fulfillment; models/human input cannot lift the existing hold.
- Customer order SO-4821:180 Friday10:00 +240 Friday16:00 =420. Released stock
  covers the first delivery; original second-window shortfall240.
- Separate replacement lot L-1058:300 offered, collection possible; arrival
  and incoming acceptance unconfirmed. Dedicated quote$3,600 against$2,500
  planner authority. No approved concession.
- Customer disposition of shipped suspect units unknown; notification pending
  responsible Quality contact. Quality owns hold, inspection and disposition.

Keep containment of shipped exposure separate from delivery replenishment,
even after schedule relief. All records/amounts/IDs/times are hypothetical.
No AI release, notification, customer commitment, real plant write or spending.
V1/site/Actions unchanged; no push/merge/publication or Azure/access changes.

## Actual framework, configuration and dependencies

Same maximum three specialists (Supply-chain, Production, Commercial) and
one Coordinator. Real `agent_framework.Agent`, isolated instructions/histories,
`OpenAIChatCompletionClient`, annotated `@tool` functions and structured
`Agent.run(options={"response_format": OutputType})` results through
`response.value`. Specialists run sequentially; Coordinator has no tools.

Real `WorkflowBuilder`, typed custom `Executor`/`@handler` messaging and
complete join. Decision-1 remains a typed scoring executor using
`POST /providers/microsoft/v1/systemone`, not a chat client.
HITL uses `ctx.request_info`, typed `@response_handler` and the same workflow's
`run(stream=True, responses={request_id: response})`. One resume only; no
checkpoint/restart, manager replanning, debate or extra summarizer model.

Core1.21.0/provider1.15.0 remain the user-approved configured-feed pins
(provider1.16.0 was unavailable). Actual installed compatibility was verified
offline in the first implementation. OpenAI SDK3.26.0 / HTTPX2 2.13.1 transport
pins remain unchanged, Python3.11+. No feed/TLS bypass or new packages.

Preserve `FOUNDRY_ENDPOINT`, `DECISION_DEPLOYMENT`, `LLM_DEPLOYMENT` and matching
CLI overrides. Both families exclusively use existing Azure Foundry resources:
Decision-1 Entra scope `https://cognitiveservices.azure.com/.default`;
GPT scope `https://ai.azure.com/.default`, explicit Azure `/openai/v1/` URL,
injected `AsyncOpenAI`, retries disabled, guarded transport, no ambient public
OpenAI URL/key fallback. AzureCliCredential process timeout15s; no identity/
resource changes. HTTPS resource-root validation, no redirects, close clients.
`--example quality-hold`; `--example supply-chain` remains an alias.

## Typed records and boundaries

Strict frozen Pydantic records reject extras, coercion, negative/invalid
quantities and unsupported scenario/tool IDs. Four existing read-only tools
accept only `scenario_id: Literal["quality-hold-v2"]`:

| Tool | Evidence | Allowlist |
| --- | --- | --- |
| read_inventory | Incident/lot reconciliation, measured sample, held versus separately released inventory | Supply-chain, Production |
| read_shipment | Shipped-suspect lot/ASN, unknown disposition/pending contact, distinct-lot replacement offer/quote, unconfirmed arrival/acceptance | Supply-chain, Commercial |
| read_build | Dated order lines, quantities, replenishment eligibility | Production |
| read_approval_policy | Planner limit/owner, Quality/contact ownership, no concession, unknown customer flexibility | Commercial |

Source `synthetic_fixture`, immutable evidence IDs and frozen snapshot on every
record. Canonical fixtures supply numeric constraints and deterministic demand
arithmetic; do not duplicate stale shortage constants in coordinator context.
Derive required unknowns from genuinely missing fields, not a hardcoded
requirement to keep known evidence uncertain. Offer quantity is not stock.

`ExpertFinding`: identity/revision, concise evidence assessment and separate
implication (each<=500 chars), action, citations, unknowns, approvals/conflicts.
`CoordinatedProposal`: revision, action, brief<=1000 chars, every participating
finding reference and preserved evidence/unknown/approval/conflict unions.
Both have strict `uses_held_stock`, `uses_expedited_freight`, `containment_required` and
`changes_customer_commitment` booleans. Host rejects held-stock use or omitted
containment; coordinator cannot clear required flags/unions. Citation/revision
checks bind to actual tools/overlays. Previous unknowns cannot disappear without
relevant cited clarification; previous conflicts remain preserved.
No blind display truncation or hidden JSON/prose repair.

Actions include containment/recovery, customer-window review, freight authority,
conditional expedited freight, schedule revision and evidence gathering.
Approvals: quality_containment, customer_notification, customer_commitment,
freight_authority. Missing arrival/acceptance/customer disposition remain
unknowns, distinct from approval authority and selection uncertainty.

## Selection, policy and one clarification

Unchanged independent Decision-1 supply_chain_needed/production_needed/
commercial_needed questions. Complete finite option distributions summing
to1 within.001; >=.70 and uniquely highest for effective needed/not-needed
or satisfactory positive validation. Explicit cannot_determine, low or tied
scores pause; malformed responses fail explicitly. Probability versus
model-reported confidence stay separate. The.70 policy is illustrative, not
calibrated quality, compliance or safety assurance.

Uncertain selection pauses before GPT, retaining confirmed-needed roles.
All not-needed ->handoff. Otherwise experts ->complete join ->Coordinator
->Decision-1 validation against original issue, canonical records, findings,
overlays and actual proposal. Host checks policy independently. Do not script
particular live selections, recommendations or validation verdicts.

User-directed UX revision: recommend contacting the customer planner to discuss
rescheduling the second240, retaining first180 Friday10:00. Preserve actual
model findings/proposal; unless the Coordinator action requests a customer-window
review, label this explicitly as a host-suggested review step, not a model
recommendation. Explain the canonical240 shortage without inventing customer
agreement or a model verdict. Keep mandatory handoffs in plan/final and use one
concise reminder about planning-only updates and separate quality/approval ownership.

Two terminal choices: record a customer response received after contact (not
intent to contact), or reject the recommendation and request leadership
escalation. First choice collects quantity, revised time and bounded response
reference in separate readable fields. All fields share one human deadline and
produce one typed response. Second choice yields `HumanResponse(kind="escalate")`
and final escalation without refresh/model calls or an actual notification.
Reject/escalate is also available during field collection.
Strict `CustomerDeliveryChange`: customer_agreed boolean; quantity integer;
offset-aware revised timestamp or null; nonempty reference<=200 characters.
An agreed move is positive, <=second-delivery quantity and later than its
original time. First delivery cannot be modified. Internal typed no-agreement
records remain supported; the terminal offers only the two choices above.
No raw JSON input, approve/release action, reprompt or additional question loop.

`HumanResponse` clarify carries only this typed customer_delivery_change.
Record `HumanEvidence {evidence_id,key,value,source=human_clarification,
request_id,revision=1}`. Reference/text is untrusted, never authority.
Deterministic map refreshes Production+Commercial, reuses Supply-chain.
Initial selection uncertainty activates mapped roles union confirmed-needed
roles, preserves unrelated uncertainty and never invents improved scores.
Coordinator/validation repeat once; then final handoff, no second request.

The illustrative240 move yields provisional original-window shortfall240->0,
not180->420 usable stock. First180 Friday10:00 unchanged; later240 still
need replenishment. Mandatory Quality containment and responsible notification
remain. Reported agreement still requires formal customer-window review.
Freight actions/dependencies above limit require operations authority, including
courier reliance within a broader containment/recovery action; no customer input can
release held stock, satisfy concessions, approve spending or perform contact.
Positive validation cannot close those owner handoffs.

## Presentation, failures and finite costs

Business sections CASE / TEAM / FINDINGS / INITIAL PLAN / HUMAN CLARIFICATION /
UPDATED HANDOFF, with evidence/implication per role, before/after, explicit
refreshed/reused findings, actual recommendations/verdicts and unresolved owner
actions. Compact chosen probability/confidence separately in normal mode.
`--verbose`: full distributions, provenance/records, request IDs, counters and
tool diagnostics. Quota waits, errors and actual totals visible normally.
Render structured results directly; no extra model calls or cosmetic sleeps.

Same caps: <=3 GPT attempts/2 unique tools/2 rounds per specialist invocation,
>=1 successful tool; Coordinator<=1 GPT, no tools. Hard totals<=20 GPT,
<=3 Decision-1,<=23 actual model attempts,<=12 tool executions. Failed attempts
and tool-result turns count cumulatively across resume. Framework
max_iterations=3/max_function_calls=2 supplemented with pre-dispatch guards
because framework can force an additional final completion or process a batch.
No retries/repair calls. Process-local rolling60s limits10 GPT/20 Decision-1.
Other callers can cause429; stop without retry.

One batched tool round per selected specialist: all-three initial7 GPT+2 D1;
Production/Commercial refresh adds5 GPT+1 D1. These are illustrative normal
paths, not guaranteed live counts or latency. Worst-case calls can take minutes.
Request60s, credential15s, tool2s, active900s including quota/auth waits,
human300s, wall1200s. Human wait pauses active clock only.
Non-TTY/EOF/interrupt/invalid/empty/expired input stays pending, no reprompt.
Auth/HTTP/TLS/timeout/refusal/truncation/schema/citation/tool/join/budget
failures stop explicitly, no partial-success fallback. Output<=1200 tokens per
GPT attempt, storage disabled. Exit0 advisory or explicit reject/escalate;
exit1 error; exit2 pending/handoff. No live inference authorized by this revision.

## Offline acceptance and grounding

Real framework agents/tools/executors/HITL with fake Azure credentials/transport:
lot720+240=960 and delivery180+240=420; held excluded; sample not total rate;
first180 covered, baseline gap240; typed customer quantity/window; mapping,
reuse and one resume; containment after schedule relief; hostile references
cannot release/spend; refreshed unknowns/conflicts retained; default/verbose
rendering and natural input; Azure-only URLs/scopes and actual caps; failure,
quota/deadline/cleanup and unchanged v1. No fabricated live transcript.

Primary IATF-hosted research supplied by the coordinating conversation:
- [Ford June2026 CSR](https://www.iatfglobaloversight.org/wp/wp-content/uploads/2026/06/Ford-IATF-CSR_Jun-2026-SCCAF_Final.pdf):
  p32 lot traceability; p34 8.7.1.1 Ford-specific concessions; p35 8.7.1.6
  shipped-nonconforming notification. WERS/PPAP and24-hour rules are
  Ford-specific, not generic constraints imposed on this fictional customer.
- [GM October2025 CSR](https://www.iatfglobaloversight.org/wp/wp-content/uploads/2025/10/IATF-16949-GM-Customer-Specific-Requirements-October-2025.pdf):
  p24 10.2.3 containment/problem-solving, multidisciplinary review and verified
  root cause. The demo does not invent root cause or conduct Quality disposition.

Microsoft API grounding from the original verified implementation:
[orchestrations](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/),
[HITL](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop),
[OpenAI provider](https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/model-providers/openai),
[structured output](https://learn.microsoft.com/en-us/agent-framework/agents/structured-output),
[tools](https://learn.microsoft.com/en-us/agent-framework/agents/tools/function-tools),
[Decision-1 REST](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision).
