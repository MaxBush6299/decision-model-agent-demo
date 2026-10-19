# Role-specific, option-scoped findings

**Status:** Written specification approved; implemented and verified offline.
Separately authorized live tests completed, but live acceptance is not achieved.

The user approved focused output-contract changes after two instruction-only
live tests failed, then selected role-specific, per-option findings. Further
live calls are paused pending separate approval. This revision addresses the
two-option Production/Pull-forward cases, not the overall orchestration.

## Problem and chosen approach

The current finding combines comparative prose with one nullable option ID
and universal dependency flags. A conditional freight claim can consequently
become an unscoped requirement, while Production is asked to populate freight
fields outside its role. Coordinator then drops or misapplies those claims.
More instructions did not establish reliable adherence.

Requiring one selected option would be smaller, but would force specialists
to recommend when their contribution is comparing alternatives. Instead,
each role assesses both supplied options in its own typed contract. An
optional preference is separate from the scope of factual claims.

## Output boundaries

Use these new specialist outputs only when canonical build/shipment records
contain actual alternatives. Quality-hold and single-plan cases retain the
existing `ExpertFinding` contract and safeguards.

Each new finding contains the supplied actor/revision, concise overall
assessment/implication, an optional `preferred_option_id`, global evidence IDs,
unknown keys and conflicts, and exactly one assessment per canonical option.
Each assessment has a non-null `option_id`, concise evidence-backed conclusion
and citations. Duplicate, missing or unknown option IDs are contract failures;
preference does not select which assessment's claims are retained.
Any non-null preference must also name a supplied option. Specialists retain
their current tool allowlists, successful-read requirement and executed-record
citation boundary, including citations nested inside option assessments.
Actually supplied issue/human evidence remains citable; unexecuted other-role
records do not become specialist evidence.

| Role | Per-option typed claims |
| --- | --- |
| Supply-chain | Aggregate incremental freight when supported, `uses_alternative_carrier`, `uses_expedited_freight`. Explain material availability, carrier/cutoff/arrival feasibility and scope limits. No production or approval-request fields. |
| Production | Required cell minutes, available cell minutes, packing minutes and ready time when supported; `uses_alternative_cell`, `requires_overtime`, `displaces_other_orders`. No operational approval-request fields. Cell usage excludes separately scheduled packing, and the cell window cannot extend beyond availability/staffing bounds. |
| Commercial | `pulls_order_forward`, `changes_customer_commitment`. No operational approval-request fields or manufacturing/expedited-service dependency fields. |

Unsupported numeric/time measurements are nullable and must be explained,
not invented. Per-option dependency claims distinguish true, false and unknown
(`null`); an unknown selected-option claim requires review, never a false
default. Claims remain model-generated and subject to canonical disagreement
checks. Other-domain limitations belong in the explanation, not fabricated
claims. New contracts reject fields owned by another role.
No action, preference or finding grants execution/customer/spending authority.

After an authorized live response exceeded the new300/200-character prose caps,
the user approved aligning specialist text fields with the existing500-character
legacy bound. That intermediate bound was subsequently superseded by explicit
user direction to remove generated prose character caps. Generated assessments,
implications, option narratives, proposal briefs and conflict descriptions now
require nonblank strict strings with no maximum character count. Prompt concision
is soft style without numeric character instructions. The1,200-token ceiling,
incomplete-finish failures and all non-prose constraints remain unchanged.

Global uncertainty/conflict preservation remains unchanged. Safety claims
such as held-stock use or containment remain explicit at finding level and
retain existing guards. A bounded global `safety_approval_requests` field retains
Quality-containment/customer-notification requirements independently of option
selection; it cannot carry freight or production approval requests. No Quality
requirement is imposed on healthy fixtures.

## Coordinator and host behavior

Coordinator receives both assessments from every participating role, with
their source IDs and optional preferences, plus its existing canonical
records. It still returns the existing model-generated proposal, selects a
supplied option and explains its tradeoff. No preferred answer is supplied.

The join checks each participating role's assessment for that selected option.
True dependency flags in that assessment must be preserved; claims from the
other option do not become chosen-plan dependencies. Operational approvals in
scoped cases now come from sourced host checks, as approved in the A+B revision.
Global unknowns, conflicts and safety requirements remain preserved.
Finding references retain actor/revision identity. With no specialist in a
domain, Coordinator uses supplied canonical evidence, not fabricated findings.

Selecting the relevant source assessment is a scope lookup, not a rewrite of
model claims. The host does not calculate replacement flags, clear approvals
or synthesize successful outputs. Unsupported retained claims remain visible
as conflicts/review. Existing independent canonical checks and Decision-1
validation still gate completion. Missing selection remains business review;
malformed output or an omitted required claim stops explicitly without repair.

Production's numeric claims are compared with canonical cell/run/packing/
reservation/readiness checks. Selected-option disagreement or unsupported
measurement prevents plan-ready output, even when its dependency flags happen
to agree. Analogous freight-total disagreement must also remain visible.
Unselected-option differences are displayed without becoming dependencies of
the chosen option; genuine global conflicts/unknowns are still preserved.
Source/model measurements are retained for inspection, not silently overwritten.

## Integration and compatibility

Select the response model by actual scenario structure and actor, never an
expected route count. Update state typing, emitted instructions, Coordinator
payload, evidence validation, selected-option joins and terminal findings
together. Preserve v1, scenario facts/selectors, routing decisions/thresholds,
four allowlisted tools, existing agents/framework graph, Entra/Foundry config,
one human continuation and Quality conflict/containment behavior.

No new model call, tool, retry, repair loop, dependency or hosted component.
Keep20 GPT/4 Decision-1/12 tool ceilings,1,200 output tokens and existing
request/token/time pacing. Keep explanations compact; verify representative
two-option payloads fit the existing request budget rather than raising it.
If a response is truncated or cannot fit the budget, fail explicitly.

Implementation retains offset-aware timestamp types and all local validation
bounds except generated prose maxima. New finding wire schemas omit unsupported JSON Schema constraints
(including `format` and length/range limits), following the
[Microsoft Learn structured-output subset](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/structured-outputs#supported-schemas-and-limitations);
the actual framework-emitted schema is checked offline. This serialization
adaptation does not normalize claims or relax local output validation.

## Offline acceptance and live boundary

Tests use the actual framework with fake external transport. Cover both
options for each role; absent preferences; wrong-role fields; duplicate,
missing and unknown IDs; tool/citation bounds; protected reservations and
packing arithmetic; mismatched costs/times/dependencies; exact selected-option
join preservation and global conflicts; skipped-role/Coordinator-only paths;
unchanged Quality/HITL/single-plan behavior, quotas and no retries.

Replay the structural failures from the retained live captures as test data:
split freight versus full freight, unscoped conditional claims,180 versus210
cell/packing confusion, and dropped material requirements. Update fake provider
outputs honestly to the new shape, not to hide negative cases. Run the full
v1/v2 suite and CLI/help checks.

Offline completion is not live acceptance. No additional inference is
authorized by this spec. Report implementation as offline-verified until a
separately approved bounded live test confirms actual model behavior; no claim
of stable routes, calibrated confidence, operational safety or guaranteed
success follows from changing the contract.

Implementation verification:163 offline tests cover v1/v2, including actual
framework transport boundaries and representative compact join request sizing.
CLI/help, installed-package consistency and diff checks also pass. Two later,
separately authorized contract tests were performed: the first stopped on prose
bounds; after the explicitly approved fix, the second reached final validation
and returned pending review. Scope/joins held, but Production numeric/time errors,
Commercial unknowns/unsupported authority requests and Coordinator contradictions
prevent live readiness. See `docs\v2.md` for exact observations. No additional
test is authorized by this specification.

19 October follow-up: the user separately approved sourced arithmetic/authority
grounding and one live run. Existing build tools now expose canonical calculations;
joint Commercial checks appear only after both shipment/policy reads. No new
source access, option selection or output normalization is introduced.166 offline
tests pass, including actual framework payload/source-boundary checks. The one
live run stopped at Supply's527-character prose versus the retained500-character
bound, before downstream grounding could be assessed. Live acceptance therefore
remains unachieved; no further inference is authorized.

The subsequent user-requested character-cap removal is verified by167 offline
tests, including long scoped/legacy/Quality/proposal/conflict narratives, retained
empty/type rejection and actual emitted schemas without prose `maxLength`.
The retained527-character live response parses unchanged and passes its existing
typed Supply/citation/option checks offline. This does not establish downstream
business validity or live readiness. No new live inference was authorized or run.

A later explicit user authorization covered one live test on `92d8fe0`. It
completed all three specialists, Coordinator and final validation without prose
or token truncation. Production typed150/180/60/Thursday18:00 and Commercial
commitment flags matched canonical evidence. However, contradictory Production
prose and unsupported production/freight approvals remained; Coordinator retained
requests without exposing contradictions. Final Decision-1 chose Needs revision
at76.8%; pending/exit2,3 Decision-1/7 GPT/6 tools,194.5 seconds. This demonstrates
live progress on typed arithmetic, not complete business-reasoning acceptance.
No additional inference is authorized by this record.

## User-approved A+B revision: prompts and sourced approvals

Replace the layered instruction blocks with one eight-sentence positive prompt
per actor. Specialists report supplied derived figures directly rather than
re-deriving arithmetic in prose. Production owns cell/packing/readiness;
Supply-chain owns inventory/shipping; Commercial owns customer meaning.
Coordinator owns sourced reconciliation and the selected-option join.

Remove scoped Production/Commercial `approval_requests` entirely, preserving all
other output fields and legacy/Quality contracts. Derive operational approval
handoffs from fixture authority, qualification, capacity, material, reservation
and customer-permission/window checks. Coordinator receives sourced per-option
requests; its unchanged proposal field remains raw auditable output, not the
source of host operational handoffs.

Supply every measurable specialist mismatch/null claim, including unselected
options, as an exact source-cited `proposal_feedback` conflict for Coordinator
to reproduce. Require any unsupported retained proposal approval to be represented
as an explicit sourced conflict. Missing required approvals or disagreement
conflicts fail without repair. Preserve model flags and numeric claims unchanged;
independent contradiction review remains, including authority-seeking actions.
Narrative reconciliation remains a model responsibility, not a claimed general
natural-language verifier.

174 offline tests pass, covering strict schema field removal,1800<=2500 versus
actual authority failures, qualified-cell/customer failures, conflict omission,
unselected nulls, unsupported retained requests, raw claim retention, short prompt
delivery, Quality/HITL, budgets and v1 behavior. No live inference is authorized
or performed for this revision. Live readiness remains unverified.

Later explicit authorization covered exactly one live run on `7abe954`.
All three specialists and final validation executed; sourced operational approvals
and actual handoffs were empty, Production arithmetic/prose matched its figures,
and Coordinator preserved both supplied Commercial disagreements as exact conflicts.
However, Commercial customer/pull-forward flags were wrong, Coordinator selected
split-standard with expedited/alternative flags true, and Supply misdated shipment
events in prose. Raw Needs revision69.6% and independent contradictions produced
pending/exit2. The run used3 Decision-1/7 GPT/6 tools in197.0 seconds, without
truncation, contract failure, retry or output mutation. No subsequent code/prompt
change or additional inference followed. Full observations are in `docs\v2.md`;
live readiness is not achieved.

## User-directed optional GPT-6 Luna profile

The user requested a different GPT backend and subsequently authorized up to five
bounded pull-forward live tests after deployment/configuration/offline checks.
Resource-specific discovery verified `gpt-6-luna` version `2026-09-22` in East US,
with available DataZoneStandard quota. A separately approved deployment,
`specialist-llm-luna`, was provisioned with capacity10 and returned10 RPM/10,000
TPM. Existing GPT and Decision-1 deployments are preserved.

Reuse the deployment env/CLI override and add explicit `LLM_PROFILE` /
`--llm-profile gpt-6-luna`; `standard` stays the default. Luna uses low reasoning
effort, no optional temperature and the unchanged1200-token total completion
allowance (reasoning plus visible tokens). Keep actual-framework tools, schemas,
prompts, approvals, contradiction guards, pacing/call/time limits and Entra auth
unchanged. No retry, repair or normalization; truncation remains explicit failure.
Stop live tests on full acceptance, auth/quota/deployment error or an identical
clearly model-related failure. Record actual observations, not provisioning as
proof of quality; no code/prompt/schema changes between live runs.

The first authorized live run on `6753de5` stopped after2 Decision-1 /1 GPT
attempts,0 tools,5.468 seconds. Despite the general GPT-6 feature table listing
tools and reasoning support, this deployed service rejected function tools with
low reasoning on Chat Completions (HTTP400), directing callers to Responses or
reasoning `none`. No specialist finding, Coordinator join or final validation
was produced.176 offline tests had passed, but cannot establish provider-specific
compatibility. No subsequent code/prompt/schema change or extra inference was
made; four unused runs were not spent on an identical request. Luna remains
blocked pending a separately approved compatibility change, not business-ready.

The user subsequently explicitly approved moving Luna to Responses while
retaining reasoning and guards. Use the installed `OpenAIChatClient`, verified
against Microsoft Learn's current framework integration reference, rather than
the older `OpenAIResponsesClient` name absent from this installed package.
For Luna only, allow `/openai/v1/responses`, emit `reasoning.effort=low` and
`max_output_tokens=1200`, and check native completed function/message output
before parsing/execution. Keep `store=False` and encrypted stateless reasoning
replay, with no hosted tools or server conversation IDs. Reject incomplete,
refused/failed/malformed output explicitly. Include replay/output allowance in
the same10,000TPM pacing; retain all role tools/caps, schemas, prompts, source
guards, Entra credentials and Decision-1/default Chat Completions behavior.
Resume the existing bounded live allowance only after offline verification.

180 offline tests passed. Subsequent live runs2/3 on unchanged `e8ee569` completed
all three specialists and produced Coordinator responses through Responses;
7 GPT /6 tools per run, all HTTP200/completed, no truncation. Typed per-option
arithmetic, dependency and sourced-approval checks matched canonical evidence.
Run2 retained Supply's cross-domain `production_capacity` unknown despite
Production's proven figures; final Decision-1 Needs revision76.3346%,
pending/exit2,3 Decision-1 calls,204.078s. Run3 Supply again marked capacity
unknown and also `qualified_cell`; Coordinator omitted both, so the existing
preservation guard failed before final validation,2 Decision-1 calls,197.578s.
Run2 also misdated the protected reservation as Friday in Supply prose.
The repeated underlying unknown-boundary problem had different terminal symptoms;
the two remaining possible runs were not spent chasing a pass. No subsequent
code/prompt/schema changes, repairs or raw claim normalization occurred.
Responses compatibility is live-verified, not business readiness. Full per-run
usage/latency/results and remaining limitations are recorded in `docs\v2.md`.

## User-directed scoped unknown ownership

The user selected single-domain ownership of specialist unknowns, offline only.
Define one immutable owner for every existing unknown key: Supply owns shipment/
acceptance/carrier/window/material allocation; Production owns capacity/
qualification/other-order impact; Commercial owns customer disposition/delivery
change/request; `proposal_feedback` is Coordinator-only. No new unknown keys or
wire schema keywords are introduced. Apply this to the existing scoped two-option
contracts, including Production-resequence, while preserving Quality and legacy
single-plan behavior.

Append concise owned-key guidance only to scoped specialist prompts: state
other-domain evidence limits in prose instead of raising them as unknowns.
Use the same owner mapping for scoped canonical required unknowns, preventing
overlapping prior domain checks from generating foreign-key instructions.
The existing option-finding validator rejects foreign-domain `unknown_keys`
with actor/key/owner details before Coordinator dispatch, without modifying
the response, clearing claims or making a repair call. This fail-closed
contract boundary matches existing option/provenance guards; do not convert
an invalid owner into an invented sourced business conflict.

Coordinator must still preserve all accepted owned unknowns; its existing
unknown/conflict preservation and human-review semantics remain unchanged.
Conflict subjects are not restricted by this unknown-key ownership rule.
Test complete key coverage/ownership, unchanged raw findings, both API paths,
canonical required-key ownership, correct Coordinator propagation/rejection,
and Quality/legacy regressions. Keep all tools, prompts outside this scoped
addition, caps, auth, Luna Responses and default Chat Completions setup unchanged.
No live inference is authorized for this revision; two remaining possible
runs stay unused until the user separately confirms their use.

185 offline tests pass. Original prior-live Supply findings replay unchanged
and fail specifically on foreign Production keys; the corresponding original
Production findings pass the ownership/option contract. No new inference or
live-readiness claim is implied.

Later explicit authorization covered exactly run4 on `5f47005`. Supply completed
with empty unknowns/conflicts and passed scoped ownership/option validation;
its cross-domain production limit stayed in prose. Production read both tools
but its second HTTP200 response was `incomplete` / `max_output_tokens`, reaching
the unchanged1200-token total allowance (425 reasoning tokens included) and
ending mid-field. The transport failed closed before parsing; no Commercial,
Coordinator or final Decision-1 execution followed. Partial Production prose
also confused separate packing readiness at18:00 with cell occupancy ending17:00;
that unaccepted claim was not normalized or treated as a validated conflict.
The run used2 Decision-1 /4 GPT attempts and4 tools in80.156s. No code/prompt/
schema change, retry or additional inference followed. One possible run remains
unused pending separate confirmation; live acceptance is not achieved.

## User-approved Luna-only 2400-token allowance and final run

Following run4's incomplete response, the user authorized raising Luna Responses
to2400 total output tokens (reasoning included), leaving default Chat Completions
at1200, then consuming exactly the fifth/final run. This supersedes earlier
Luna-specific1200-token statements, not historical live observations.
A single profile property supplies the framework allowance, numeric-only prompt
budget replacement and startup display. Preserve all other prompt content,
schemas, ownership/provenance/business guards, tools, auth and low reasoning.
Native `max_output_tokens` already feeds conservative TPM estimation; reserve
the full2400 plus serialized input within the unchanged10,000TPM ceiling,
including fail-before-dispatch for oversized single requests. Do not raise
call/tool/time limits or relax incomplete/truncation rejection.
186 offline tests pass before the final authorized run. No further code/prompt/
schema changes, retries, repair or normalization are authorized during or after
that run. Record actual results without a readiness claim unless acceptance
fully passes; all prior live authorization is consumed when run5 executes.

## User-approved diagnostics and up to two additional live runs

Run5 failed on Production's second request without a captured complete response
or underlying exception chain; the exact cause was not established. Subsequent
explicit approval permits diagnostic-only instrumentation, then at most two new
Luna Responses pull-forward runs after offline verification. Preserve sanitized
exception types/messages/causes through runtime, SDK/framework and GPT boundaries,
HTTP status/body when present, native status/incomplete reason, request correlation
and transport/read latency. Capture partial failures before/while reading bodies.
Redact credentials, tokens, endpoint URLs, provider/continuation IDs and opaque
encrypted reasoning from independent copies; never mutate actual model outputs.
192 offline tests pass, including timeout/transport/HTTP/incomplete/partial-read
failures and no-retry behavior. Prompts, schemas, ownership, budgets, pacing,
tools, auth and fail-closed guards remain unchanged.

Number new observations from run6. No retries/repair/normalization or changes
between runs; stop early on full acceptance, or after the first auth/quota/network
failure for user decision. Use a second run only if the first does not pass and
distinct model failure evidence or needed diagnostics justify it. Report actual
specialist completion, ownership/conflicts, final verdict if reached, timings
and known versus unavailable usage. This approval does not imply demo readiness.

Run6 on `7c0e998` completed all three specialists with owned unknowns/conflicts
empty and no typed source discrepancies, including correct150/180 cell minutes,
60 separate packing minutes, Thursday18:00 readiness and1800/0 freight within2500
authority. Coordinator dispatch was blocked by the unchanged local10,000-token
single-request estimate. Offline framework reconstruction with the saved findings
gave25,625 request bytes /8,542 estimated input +2,400 output =10,942; no live
Coordinator or final Decision-1 verdict exists. Diagnostics retain the framework
and local-budget exception types/messages. Attempts2 Decision-1 /6 GPT,6 tools,
314.750s; all dispatched calls HTTP200. The second newly authorized run remains
unused under the non-model quota/budget stop rule, pending user decision.
No code/prompt/schema/budget change or retry followed; acceptance is not achieved.
