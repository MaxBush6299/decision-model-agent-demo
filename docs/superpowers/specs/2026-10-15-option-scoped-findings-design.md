# Role-specific, option-scoped findings

**Status:** Written specification approved; implemented and verified offline.
Live acceptance remains pending separate authorization.

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
| Production | Required cell minutes, available cell minutes, packing minutes and ready time when supported; `uses_alternative_cell`, `requires_overtime`, `displaces_other_orders`; only `production_authority` approval requests. Cell usage excludes separately scheduled packing, and the cell window cannot extend beyond availability/staffing bounds. |
| Commercial | `pulls_order_forward`, `changes_customer_commitment`; only `freight_authority`/`customer_commitment` approval requests, grounded in its shipment/policy evidence. No manufacturing or expedited-service dependency fields. |

Unsupported numeric/time measurements are nullable and must be explained,
not invented. Per-option dependency claims distinguish true, false and unknown
(`null`); an unknown selected-option claim requires review, never a false
default. Claims remain model-generated and subject to canonical disagreement
checks. Other-domain limitations belong in the explanation, not fabricated
claims. New contracts reject fields owned by another role.
No action, preference or finding grants execution/customer/spending authority.

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
True dependency flags and approval requests in that assessment must be
preserved; claims from the other option do not contaminate the chosen plan.
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
bounds. New finding wire schemas omit unsupported JSON Schema constraints
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

Implementation verification:162 offline tests cover v1/v2, including actual
framework transport boundaries and representative compact join request sizing.
CLI/help, installed-package consistency and diff checks also pass. No new live
call was made; previous instruction-only failures remain unresolved acceptance
evidence until an authorized test exercises this revision.
