# Option-Scoped Findings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ambiguous comparative specialist outputs with role-owned,
per-option claims while retaining raw model evidence and existing safety gates.

**Architecture:** Two-option scenarios use three strict specialist response
models, one per role. Coordinator still returns the existing proposal; join
validation selects matching source assessments, and independent fixture checks
surface incorrect/unknown claims without rewriting them.

**Tech Stack:** Existing Python/Pydantic, Microsoft Agent Framework and
Foundry/Entra adapters; standard-library unittest and existing fake transport.

**Execution status:** All three tasks completed inline with test-first contract,
framework and presentation coverage;163 offline tests pass. New finding wire
schemas exclude unsupported Foundry keywords while local validation retains
bounds/aware timestamps. Subsequent explicit approvals covered one contract live
test, then the500-character prose-bound fix and one further live test. The latter
reached final validation but retained business contradictions; live acceptance
is not achieved. Full observations are recorded in `docs\v2.md`.

**19 October follow-up:** Separately approved sourced grounding is committed as
`3bd6b2e`;166 offline tests pass. The single authorized live test stopped on
Supply's527-character assessment exceeding the retained500-character bound.
Downstream live effectiveness is unobserved. No retries or additional inference;
this is a blocked acceptance result, not a ready demo.

**Subsequent user-directed change:** Remove generated narrative character caps
across scoped/legacy/Quality findings, per-option assessments, proposal briefs and
conflict descriptions. Retain nonblank strict strings, the1,200-token allowance,
all input/ID/reference/list/provenance/business guards and incomplete-finish
failure.167 offline tests pass; the saved527-character response replays unchanged.
No live inference was performed or authorized for this change.

## Global Constraints

- Approved spec: `docs\superpowers\specs\2026-10-15-option-scoped-findings-design.md`.
- Quality-hold and single-plan cases retain the existing `ExpertFinding` contract.
- Claims remain model-generated; no replacement flags or synthesized success.
- No new model call, tool, retry, repair loop, dependency or hosted component.
- Keep20 GPT/4 Decision-1/12 tool ceilings,1,200 output tokens and existing pacing.
- Preserve v1/site, fixture facts, routing probabilities/thresholds and Entra config.
- No live inference until separately authorized; offline completion is not readiness.
- Work only in the current isolated v2 branch; commit locally with session trailers.

## File responsibilities

| File | Change |
| --- | --- |
| `decision_v2\contracts.py` | New role-owned option/finding types, union state typing, scoped reference/ID validation, matching-option claim lookup and proposal preservation checks. |
| `decision_v2\agents.py` | Actual actor/scenario response-model selection, scoped instructions, nested citation checks and preservation of the concrete refreshed model type. |
| `decision_v2\fixtures.py` | Compare model option claims/measurements with existing canonical option calculations; do not mutate records or claims. |
| `decision_v2\workflow.py` | Include selected scoped disagreements/unknowns in review reasons even with positive model validation. |
| `decision_v2\presentation.py` | Render per-option claims, optional preference and unsupported/disagreeing evidence without implying a selected/executed plan. |
| `test_decision_v2.py` | Literal valid role outputs, adversarial contract/join cases and actual-framework provider coverage. |
| `docs\v2.md` | Document the new boundary and offline/live distinction. |

### Task 1: Strict role-owned option contracts

**Interfaces produced in `contracts.py`:**

- `SupplyOptionAssessment`: `option_id`, concise `assessment`, `evidence_ids`,
  nullable finite nonnegative `freight_total_usd`, nullable
  `uses_alternative_carrier`/`uses_expedited_freight`.
- `ProductionOptionAssessment`: common fields plus nullable nonnegative integer
  `required_cell_minutes`, `available_cell_minutes`, `packing_minutes`,
  nullable offset-aware `ready_at`, nullable `uses_alternative_cell`,
  `requires_overtime`, `displaces_other_orders`, and bounded approval requests
  restricted to `production_authority`.
- `CommercialOptionAssessment`: common fields plus nullable
  `pulls_order_forward`/`changes_customer_commitment`, approvals restricted to
  `freight_authority`/`customer_commitment`.
- `SupplyFinding`, `ProductionFinding`, `CommercialFinding`: actor-specific
  literals, revision, concise assessment/implication, optional preference,
  evidence IDs, unknowns/conflicts, held-stock/containment safety fields and
  exactly two owned assessments. Define `ScopedFinding` as their union and
  `Finding` as `ExpertFinding | ScopedFinding`.
- `validate_option_finding(finding: ScopedFinding, option_ids: set[str],
  allowed: set[str]) -> None`: validate exact ID coverage, preference,
  nested citations and duplicate IDs.
- `OptionAssessment`: union of the three assessment models.
- `option_assessment(finding: ScopedFinding, option_id: str) -> OptionAssessment`:
  return the matching typed assessment or raise `DemoError`.
- `dependency_claims(assessment: OptionAssessment) -> dict[str, bool | None]`:
  return only fields owned by that assessment, retaining explicit nulls.

- [x] Write `OptionContractTests` before production code:

```python
def test_supply_cannot_claim_production_or_approval_authority(self):
    from decision_v2.contracts import SupplyOptionAssessment
    base = dict(option_id="split-standard", assessment="Standing service.",
                evidence_ids=["fixture:shipment:order-pull-forward-v2"],
                freight_total_usd=0, uses_alternative_carrier=False,
                uses_expedited_freight=False)
    for extra in ({"requires_overtime": False},
                  {"approval_requests": ["freight_authority"]}):
        with self.subTest(extra=extra), self.assertRaises(ValidationError):
            SupplyOptionAssessment(**base, **extra)
```

  Add literal valid instances for all roles and explicit nulls. Test missing,
  duplicate/unknown option IDs, an unknown preference, wrong revision,
  nested invented citations, offset-free ready time and invalid costs/minutes.
  Null must remain null after serialization, not become false.
- [x] Run `.\.venv\Scripts\python.exe -m unittest test_decision_v2.OptionContractTests -v`;
  observe failure because the new contract is absent.
- [x] Implement the models using existing `StrictModel`, `Conflict`, revision
  validator and evidence bounds. Use `extra="forbid"` through inheritance;
  restrict option lists to two and reject IDs at the runtime boundary, not
  through scenario-name/expected-count literals.

```python
def option_assessment(finding, option_id):
    for assessment in finding.option_assessments:
        if assessment.option_id == option_id:
            return assessment
    raise DemoError("Specialist omitted the selected planning option.")
```

  Keep global safety/unknown/conflict fields at finding level. Make new claims
  required-but-nullable where the spec permits unknown; do not add all-false
  defaults. Annotate `RunState.findings` with the new union.
- [x] Run the new contract tests plus existing `ContractTests`; inspect exact
  class names with `rg` before choosing unittest selectors.

### Task 2: Actual agents, Coordinator join and evidence review

**Interfaces consumed:** Task1 models and helpers; existing `fixture_records`,
`operational_options`, evidence ledger, `validate_proposal` and runtime budgets.

**Interfaces produced:**

- `ExpertTeam.assess(...) -> Finding`, retaining legacy behavior without options.
- `scoped_option_disagreements(finding: ScopedFinding, records,
  option_id: str) -> list[str]` in `fixtures.py`.
- Updated `validate_proposal` and `review_reasons` supporting both finding shapes.

- [x] Extend `MockFoundry` to emit the new schema only when actual alternatives
  are supplied. Keep real framework agents/tools/graph. Use hand-checked literal
  model measurements:

```python
production_measurements = {
    "cell-p2": (180, 240, 60, "2026-10-15T18:30:00-05:00"),
    "cell-p3": (250, 300, 60, "2026-10-15T19:25:00-05:00"),
    "full-early": (150, 180, 60, "2026-10-15T18:00:00-05:00"),
    "split-standard": (150, 180, 60, "2026-10-15T18:00:00-05:00"),
}
```

  Do not derive fake expected measurements using the production comparator.
  Keep explicit negative overrides for dropped true claims, extra fields and
  incorrect measurements rather than normalizing fake responses to success.
- [x] Write failing actual-framework tests proving actor-specific response
  schemas/instructions, exactly both options, no forced preference, read/citation
  enforcement, raw output retention and no provider retries.
  Replay full-versus-split freight, dropped expedited/displacement claims,
  non-owner approval attempts,180-versus210 available/work confusion and a
  wrong ready time. Test positive D1 plus bad selected evidence stays in review.
- [x] Run those targeted tests and observe failure against the old agent path.
- [x] Select `SupplyFinding`/`ProductionFinding`/`CommercialFinding` only for
  actual two-option records. Keep legacy response class otherwise. Remove
  legacy global option/flag instructions from the new path; explain preferred
  option versus per-option claims and explicit unknowns.
- [x] Validate header and nested evidence against actual executed records,
  issue and supplied human evidence. Preserve prior conflicts using the
  concrete response class, not `ExpertFinding.model_validate`.
- [x] Supply all raw option assessments to Coordinator. Its proposal schema,
  selected ID and finding references stay unchanged. For a selected option,
  join only that assessment from each participating role. Preserve each true
  owned flag and applicable approval; retain all global safety/unknown/conflict
  requirements. Missing selection remains review, not an arbitrary alternative.
- [x] Compare nullable role-owned flags and measurements without replacing them:

```python
expected = operational_options(records)[option_id]
# For the Production assessment:
checks = {
    "required_cell_minutes": expected["position"]["production_minutes"],
    "available_cell_minutes": expected["position"]["available_cell_minutes"],
    "ready_at": expected["position"]["ready_at"],
}
```

  Also compare packing against its build option, freight against aggregate
  leg cost, and owned flags against canonical dependency values. Compare
  timestamps as aware instants, not strings. A null/mismatched selected claim
  becomes a specific review reason; do not silently substitute a value.
  Keep unselected discrepancies inspectable without merging their dependencies.
- [x] Run targeted contract/scenario/framework tests, including skipped roles,
  Coordinator-only assessment, all legacy Quality/HITL regressions and budget/
  malformed-output tests. Commit the coherent typed integration with trailers.

### Task 3: Terminal output, documentation and final offline verification

**Interfaces consumed:** `Finding`, each option's raw claims and disagreement
messages, unchanged proposal and review reasons.

- [x] Write failing presenter tests expecting both option IDs, independently
  labeled model claims, an optional preference distinct from final selection,
  explicit unknowns and no legacy `recommended_action` attribute assumptions.
  Keep the old Quality output assertions unchanged.
- [x] Run the presenter tests and observe failure.
- [x] Branch `Presenter.finding` by the typed finding shape. Print overall
  assessment/implication, then compact per-option facts/unknowns and sources.
  Only label an actual preference as a preference; Coordinator alone labels
  the selected proposal. Verbose output retains complete model JSON.
  Display canonical discrepancies separately rather than editing model prose.
- [x] Update `docs\v2.md` and approved spec status. Explain role-owned claims,
  scoped preservation, explicit unknowns, unchanged legacy cases and lack of
  new live acceptance. Do not describe previous failed runs as successes.
- [x] Run the full offline suite and smallest packaging/CLI checks:

```powershell
.\.venv\Scripts\python.exe -m unittest test_decision_v2 test_decision_demo -q
.\.venv\Scripts\python.exe decision_demo_v2.py --help
.\.venv\Scripts\python.exe -m pip check
git --no-pager diff --check
```

  Exercise representative two-option requests through the actual runtime's
  request/token ceilings. Keep1,200 output tokens and all existing call caps;
  no dependency installation unless a real missing-package failure occurs.
- [x] Review final diff for fixture/v1/site/auth/budget changes, commit locally
  with trailers and verify clean status. Report offline results and explicitly
  pending live acceptance. Do not start another live test without authorization.
