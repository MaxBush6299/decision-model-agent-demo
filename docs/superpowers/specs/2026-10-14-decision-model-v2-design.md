# Decision model v2: selective expert team

**Status:** Written-spec review required before planning or implementation.

## Scope

One terminal-first synthetic shortage: 480 assemblies required tomorrow,
material for 310, shortfall 170, delayed shipment with unknown arrival,
$4,200 freight against $2,500 planner authority, and an alternate lacking
engineering approval. Recovery capacity and customer commitment are unknown.
At most Supply-chain, Production, Commercial, and one Coordinator; one initial
assessment and at most one clarification-driven continuation.

Leave v1 CLI/tests/requirements/contracts, site, and GitHub Actions untouched.
Implementation will add separate v2 entrypoint/modules/dependencies/fixture/tests.
No arbitrary custom issues, additional domains, recurring debate, web hosting,
plant writes, resource/access changes, push/merge/publication, or live model smoke.
Spec approval does not authorize live inference.

## Real framework boundaries

Use `agent_framework.Agent` with distinct instructions, isolated histories, and
`agent_framework.openai.OpenAIChatCompletionClient` for each specialist and
Coordinator. Reuse the configured GPT deployment, not a shared conversation.
Dispatch specialists sequentially in Supply-chain/Production/Commercial order:
multiple agents need not mean simultaneous network requests, and sequential
execution simplifies quotas and terminal evidence. Coordinator has no tools.

Use `WorkflowBuilder`, custom `Executor` subclasses, typed `@handler` messages,
and `WorkflowContext` messaging/output. Specialist executors invoke actual
framework agents. Join expects exactly the selected IDs, not partial successes.
Decision-1 is a typed custom executor calling verified
`POST /providers/microsoft/v1/systemone`, never a chat client.

Human review uses `ctx.request_info(request_data=ClarificationRequest,
response_type=HumanResponse)`, `WorkflowEvent.type == "request_info"`,
`@response_handler`, and the same workflow's
`run(stream=True, responses={request_id: response})`. One bounded response/resume,
not the documentation sample's unbounded loop. No checkpoint/restart feature.

Current Learn documents released `agent-framework-core` and
`agent-framework-openai` without requiring `--pre`. Provider-leading
`OpenAIChatCompletionClient(model=...)` replaces old `AzureOpenAIChatClient`
and `deployment_name`. Typed output uses
`Agent.run(..., options={"response_format": OutputType})` and `response.value`.
Annotated functions registered through `tools`/`@tool` are real framework tools.
Read-only PyPI metadata checks identify `agent-framework-core==1.21.0` and
`agent-framework-openai==1.16.0` as current releases; the latter requires
core>=1.20.0,<2 and openai>=2.25.0,<4. Both support Python>=3.10; retain the
repository's Python 3.11+ baseline. Target these exact framework pins in the
separate v2 dependency file. Tagged official source (`python-1.21.0`) confirms
the provider version and Agent/workflow/client signatures. No packages were
installed or imported, and runtime compatibility remains an offline
implementation acceptance check, not a claimed tested integration.

## Configuration and auth

Preserve endpoint/deployment flags, environment precedence, and validation.
V2 initially supports `--example supply-chain` and offline `--help`.
Keep `AzureCliCredential(process_timeout=15)`, Decision-1 audience
`https://cognitiveservices.azure.com/.default`, GPT audience
`https://ai.azure.com/.default`, deployment-name `model`, and GPT resource-root
`/openai/v1/` Chat Completions with no dated API-version requirement.

Use explicit routing/auth; no ambient public OpenAI fallback or identity change.
Tagged provider source verifies `async_client: AsyncOpenAI` injection and a
default credential audience of `https://cognitiveservices.azure.com/.default`.
Therefore inject a preconfigured `AsyncOpenAI` with the validated Azure v1 URL,
an Azure Identity bearer-token provider explicitly targeting GPT's existing
`https://ai.azure.com/.default` scope, retries disabled, and bounded transport.
Do not pass a bare credential that silently changes the GPT audience.
The injected client bypasses provider environment routing. Disable cross-host
redirects; close credentials/clients. No API keys in configuration or trace.

## Typed fixture and agent contracts

Frozen workflow envelopes; strict Pydantic model/tool schemas reject extras,
unsupported IDs, coercion, negative counts, and nonfinite values. Required
fields use explicit null for genuine unknowns. Every tool accepts only
`scenario_id: Literal["parts-shortage-v2"]`; no arbitrary path/URL/query/write.
Outputs include scenario ID, immutable evidence ID, `source=synthetic_fixture`.

| Tool | Typed fields | Allowlist |
| --- | --- | --- |
| `read_inventory` | required/available/shortfall assemblies: integers 480/310/170; alternate approved: false | Supply-chain, Production |
| `read_shipment` | status: delayed; confirmed arrival: string or null; freight USD: integer 4200 | Supply-chain, Commercial |
| `read_build` | window: tomorrow; required: integer 480; recovery capacity: nonnegative integer or null | Production |
| `read_approval_policy` | planner USD limit: integer 2500; freight/alternate approval rules: true; customer commitment: string or null | Commercial |

Host independently loads immutable fixture facts for policy. Missing fixture
or failed tool is an error; a null field is valid unknown evidence.
`AssessmentInput`: scenario/revision, original issue, allowed tools, relevant
prior findings, separately delimited clarification overlay.
`ExpertFinding`: agent ID, revision 0/1, assessment, action, evidence IDs,
known unknown keys, approval requests, conflicts.
Conflict: subject key, evidence IDs, description.
`CoordinatedProposal`: revision, action, brief, every participating agent/revision
finding reference, and evidence/unknown/approval/conflict fields.

Actions: seek_freight_approval, expedite_freight, resequence_build,
engineering_review, gather_information. Approval kinds: freight_authority,
engineering, customer_commitment. Unknown keys cover declared nullable fields,
domain uncertainty, and unresolved selection IDs. Text <=2000 characters per
assessment/brief; lists <=12 entries; <=6 conflicts with descriptions <=500.
Validate IDs/revision/citations against the actual tool/overlay ledger.
Coordinator must preserve unresolved unions and all participating findings,
not manufacture consensus or omit inconvenient evidence. Resolving an unknown
requires relevant typed evidence and a refreshed finding; conflicting fixture
claims remain conflicts.

## Selection and bounded control flow

One Decision-1 HTTP request contains independent supply_chain_needed,
production_needed, commercial_needed choice questions, each with needed,
not_needed, cannot_determine. Require complete finite [0,1] probabilities
summing to 1 within .001. Needed/not-needed becomes effective only if selected
probability >=.70 and uniquely highest. Explicit cannot_determine, low/tied
scores are uncertainty; malformed/missing answers are contract errors.
Probability and optional model-reported confidence remain separate. The .70
rule is illustrative, not a calibrated quality or safety guarantee.

Any uncertain selection pauses before GPT; retain confirmed selections, never
run everyone just in case. All confidently not-needed ends in handoff.
Otherwise selected experts -> complete join -> Coordinator -> Decision-1
validation of original issue, immutable fixture, active findings, overlay,
actual proposal, action consistency, approvals, and preserved conflicts.
Use existing Addresses the issue / Needs revision / Cannot determine rubric.
Positive validation requires the same complete-distribution/threshold rule.

Host then computes policy. Advisory completion requires satisfactory validation
and no unresolved selections/unknowns/conflicts/approvals. Otherwise request
the one human response. Clarification refreshes affected experts, reruns
Coordinator, and validates once more. Finish in advisory completion or final
handoff, never a second human-inference cycle or extra selection/replanning call.

## Human evidence and affected team

`ClarificationRequest`: allowed keys, unresolved selections/unknowns/conflicts,
validation/policy reasons, proposal reference if present.
`HumanResponse`: clarify with 1-4 typed updates, reject, or escalate; no approval.

| Key/type | Affected specialists |
| --- | --- |
| shipment_arrival: nonempty string | Supply-chain, Production |
| material_availability_note: nonempty string | Supply-chain, Production |
| recovery_capacity_assemblies: nonnegative integer | Production |
| customer_commitment: nonempty string | Commercial, Production |
| proposal_feedback: nonempty string | Active specialists; unresolved-selection specialists if none active |

Expose only request-relevant keys (mapped domain keys for selection uncertainty,
proposal_feedback for validation revision). Notes <=1000 characters.
Initial selection pause activates mapped experts union confirmed-needed ones;
unaffected uncertain selections remain unresolved and force final handoff.
Mapped activation is an application decision sourced to the clarification,
not a rewritten Decision-1 score or claim that selection probabilities improved.
Replace affected findings; explicitly reuse unaffected ones; Coordinator always
reruns. Still at most three specialists.

Record `HumanEvidence {evidence_id,key,value,source=human_clarification,
request_id,revision=1}`. Assertions are unverified evidence, not instructions.
They may fill null domain fields; notes cannot mutate counts/cost/authority/
engineering approval/tool permissions/rubric/budgets. Contradictions remain
visible. No "skip review" effect. Non-TTY/EOF/interrupt/invalid/empty/expired
input remains pending; no fabricated input, automatic resume, or reprompt loop.

## Policy and errors

Freight actions require authority review when cost exceeds limit or either is
unknown; fixture $4,200 > $2,500. Engineering review or reliance on the unapproved
alternate requires engineering review. Preserve expert approval requests even
if Coordinator chooses another action. Customer commitment changes require
Commercial review. Policy uses typed fields/immutable facts, not substrings.
Human clarification cannot satisfy mandatory approvals in this slice.
Nothing executes actions, grants spending authority, certifies safety, or
releases parts; validation is not real-world resolution.

Auth/HTTP/TLS/network/429/timeout/refusal/truncation/schema/citation/tool/unknown
call/join/budget failures stop explicitly. Detect framework tool-error content
before another model turn; no hidden repair, retry, failed-agent omission,
fabricated partial proposal, or success fallback. Cancel work/close resources.
Exit 0: advisory completion or explicit reject/escalate; exit 1: execution/contract
error; exit 2: pending/unresolved handoff. Always print actual status.

## Finite cost and time

Specialists: <=3 actual GPT attempts each (initial plus <=2 tool-result turns),
<=2 unique allowed tool executions across <=2 rounds, >=1 successful tool.
Coordinator: <=1 GPT attempt, no tools. Configure the released TypedDict
`function_invocation_configuration` with `max_iterations=3`,
`max_function_calls=2`, and `allow_concurrent_invocation=False`; disable SDK
retries. Tagged core source shows that iteration exhaustion can trigger an
additional final completion, and the tool-count limit is best-effort after a
batch. These settings alone do not enforce our ceilings. Authoritative
pre-dispatch transport/tool guards reject any fourth specialist model attempt
or excessive/duplicate/unknown tool call, even a framework-generated final
completion. Exhaustion fails explicitly; no extra completion or repair budget.

| Hard ceiling | Initial | Continuation | Total |
| --- | --- | --- | --- |
| Specialist invocations | 3 | 3 affected | 6 |
| GPT attempts | 3x3+1=10 | 3x3+1=10 | 20 |
| Decision-1 attempts | 2 | 1 | 3 |
| All model attempts | 12 | 11 | 23 |
| Tool executions | 6 | 6 | 12 |

These are worst-case limits, not expected calls or latency claims. A normal
all-three selected assessment with one tool round per expert uses 7 GPT +2
Decision-1 attempts; fewer selected experts use fewer calls. One affected expert
continuation with one tool round adds 3 GPT +1 Decision-1. Initial selection pause
skips initial GPT/validation, so continuation totals <=10 GPT +2 Decision-1.
Worst-case 23 attempts can take minutes; no extra model calls for repairs.

Count failed attempts and every actual tool-turn call; counters survive resume.
Process-local rolling 60-second pacing <=10 GPT / 20 Decision-1, bounded waits;
other clients may still cause HTTP 429 and the run stops without retry.
Request 60s, credential 15s, local tool 2s. Active deadline 900s includes quota/auth
waits; one human deadline 300s; overall 1200s. Human wait pauses only active clock.
GPT output <=1200 completion tokens per attempt, storage disabled, input bounded
by schema limits. Cancellation prevents further dispatch/background inference.

## Trace and offline acceptance

Label LIVE Azure versus MOCKED tests and SYNTHETIC tools. Trace selected/skipped/
uncertain experts, probabilities versus confidence, tool/evidence IDs, refreshed/
reused findings, conflicts/unknowns, Coordinator, validation/policy, framework
request/resume, attempts/tool counts, client timings, final status. No invented
Decision-1 explanation, hidden chain of thought, credentials/private endpoints.

Unittest uses real framework agents/workflow/HITL with fake provider transport
and credentials, not mocked orchestration. Cover selections/uncertainty/schema/
provenance/tool turns/allowlists/errors; complete join and preserved unions;
validation distributions; one resume/fixed mapping/reused findings; injection
assertions/contradictions/mandatory approvals; input termination; exact Azure
URL/audiences/no ambient fallback; failed attempts, per-agent/global/tool caps,
disabled retries, fake-clock rolling-window pacing/all deadlines/cleanup; v1
behavior unchanged. No site edits or live calls.

## Grounding and review gate

Microsoft Learn checked 2026-10-14:

- [Orchestrations](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/)
- [Human-in-the-loop](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop)
- [OpenAI provider](https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/model-providers/openai)
- [Tools](https://learn.microsoft.com/en-us/agent-framework/agents/tools/function-tools)
- [Structured outputs](https://learn.microsoft.com/en-us/agent-framework/agents/structured-output)
- [Invocation limits](https://learn.microsoft.com/en-us/python/api/agent-framework-core/agent_framework.functioninvocationconfiguration?view=agent-framework-python-latest)
- [Package/API changes](https://learn.microsoft.com/en-us/agent-framework/support/upgrade/python-2026-significant-changes)
- [Decision-1 REST](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision)
- [GPT v1/Entra](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle)

Read-only release checks on the same date:

- [PyPI core metadata](https://pypi.org/pypi/agent-framework-core/1.21.0/json)
- [PyPI provider metadata](https://pypi.org/pypi/agent-framework-openai/1.16.0/json)
- [Tagged provider version/dependencies](https://github.com/microsoft/agent-framework/blob/python-1.21.0/python/packages/openai/pyproject.toml)
- [Tagged Chat Completions signatures](https://github.com/microsoft/agent-framework/blob/python-1.21.0/python/packages/openai/agent_framework_openai/_chat_completion_client.py)
- [Tagged auth/routing](https://github.com/microsoft/agent-framework/blob/python-1.21.0/python/packages/openai/agent_framework_openai/_shared.py)
- [Tagged invocation limits](https://github.com/microsoft/agent-framework/blob/python-1.21.0/python/packages/core/agent_framework/_tools.py)

Wheel retrieval encountered a TLS handshake failure; no TLS verification was
disabled. Signature verification instead used the matching official release
tag read-only, not package installation or execution.

Self-review: bounded graph/contracts/provenance, uncertainty vs error, immutable
policy, deterministic affected team, actual attempts/timeouts, offline tests,
v1 isolation. Package metadata and tagged auth/invocation signatures verified;
installed runtime compatibility still needs offline acceptance during
implementation. No unresolved product-design decision remains.
User written-spec approval precedes writing-plans.
