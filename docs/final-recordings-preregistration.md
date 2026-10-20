# Final-recordings pre-registration (committed before any code change or live run)

Goal: at least one successful recorded run for each of quality-hold, carrier-delay, production-resequence and order-pull-forward, on hardened, frozen source.

## Definition of a "successful recorded run" (fixed now)
A run succeeds when ALL hold:
1. Correct, safety-appropriate, source-consistent outcome: every factual claim in the final output (IDs, quantities, times, costs, option comparison, unknowns, approvals) matches the fixture, with no unsupported confirmation, approval, spend or safety claim, and mandatory approvals/unknowns preserved.
2. The disposition is the right one for the scenario. A pending/handoff outcome COUNTS when it is the right disposition and its explanation is correct (e.g. quality-hold containment/approval handoff). An `advisory_complete` counts only when no mandatory approval or unknown remains.
3. It does NOT count if it fails only through a false-positive guard (warning or fatal), a typed-field/format slip, an infrastructure error, or if the output contains an incorrect or unsafe claim.
A Decision-1 "Needs revision" on a semantically correct, correctly-dispositioned run is scored as a model-validation outcome, judged by criteria 1-3 (the host disposition must still be the right one); it is reported separately.

## Selection rule
Per scenario the displayed recording is chosen by independent semantic review: a fully clean `advisory_complete` (where that is the right disposition) is preferred; otherwise a successful pending/handoff; ties go to the earliest ordinal. The viewer discloses attempts recorded vs selected and links all attempts. Failed attempts are always archived and disclosed.

## Protocol
- After offline work (Steps 2-3, committed with a green suite), up to 5 sequential runs per scenario (max 20), APIM + Luna (`--llm-profile gpt-6-luna`), `--debug`, distinct x-run-id, frozen source, no retries beyond Package A, no tuning between runs.
- A scenario may stop early once it has one successful run by the definition above; all attempts made are recorded.
- Everything stops on infrastructure/auth/routing failure.
- Archive under `decisionmodels\run-logs\apim-runs\final-recordings\` (not committed). Build the sanitized public-candidate replay projection per recording-plan.md for the selected run per scenario (unpublished).
- No publication, push or readiness claim; small-n caveat applies.

## Offline scope (before live)
- Step 2: make `prose.pickup` / `prose.booking` leg-aware for multi-leg shipments (warn only on clear contradiction with the relevant leg's source); if a rule cannot be made precise generally it becomes display-only (recorded, shown, non-blocking for `advisory_complete`).
- Step 3: narrow prompt change: Coordinator and Quality/legacy Coordinator must carry every participating dependency flag (e.g. `uses_expedited_freight`) and approvals/unknowns forward; a reference/offer is not a selectable plan; new-build vs total-coverage wording. No schema, host-preservation or approval-rule relaxation; typed/ownership/authority/preservation checks stay fatal.
- Generic synthetic tests only; no replay tuning.
