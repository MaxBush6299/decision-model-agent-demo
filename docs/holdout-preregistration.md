# Hold-out pre-registration (written and committed before any live run)

Frozen source: commit `da81ffc` on `v2-hardening-offline` (based on `apim-profile-v2` `442c7c5`).
Only docs may change after this commit. Source, prompts, schema, budgets and config are frozen.
Criteria below are not modified after any output is seen.

## Cases (fresh synthetic, same domain; never-used IDs/quantities)

Disclosure: the shared fixture snapshot day (2026-10-15 14:00 UTC-05:00) is reused; IDs, lots,
quantities, carriers, shipments and times are new.

| | `holdout-feasible` (`holdout-feasible-v2`) | `holdout-uncertain` (`holdout-uncertain-v2`) |
|---|---|---|
| Order / lot / qty | SO-7301 / L-1073 / 450 | SO-7302 / L-1074 / 380 |
| Release / shipment | QA-REL-1073 / SH-731 | QA-REL-1074 / SH-732 |
| Carrier | Fictional approved regional carrier D, slot confirmed | Fictional carrier E, slot NOT confirmed, no confirmation reference |
| Pickup / transit / arrival | 15:30 / 1050 min / Fri 09:00 | 16:00 / 1020 min / Fri 09:00 |
| Window | 08:30-10:30 | 08:30-10:30 |
| Freight | $1,350 (within planner limit) | $3,400 (above $2,500 planner limit) |
| Commitment | EDI-SCHEDULE-7301 | EDI-SCHEDULE-7302 |
| Original carrier arrival | 11:45 (misses window) | 12:10 (misses window) |

## Expected outcomes (ground truth from the deterministic fixture)

- Feasible: resolved carrier record, no unknowns, no mandatory approvals. Correct disposition: `advisory_complete`, exit 0.
- Uncertain: unknown `carrier_confirmation` (supply-chain, commercial); `freight_authority` approval required; must not claim a confirmed slot or approved cost. Correct disposition: `pending`/handoff, exit 2 (never `advisory_complete`, never exit 0).

## Protocol

- 5 sequential runs per case, feasible first then uncertain = 10 runs. Command: `python -m decision_v2 --example <case> --llm-profile gpt-6-luna --debug`.
- Through APIM (gateway/scope per run config), Azure CLI on PATH, distinct x-run-id (the v2 run id) per run.
- No retries beyond the Package A rule (Luna 120s deadline, one pre-send ConnectTimeout retry). No tuning, repair or replacement runs.
- Stop on infrastructure/auth/routing failure; samples are not replaced or extended.
- All attempts archived (stdout, stderr debug trace, exit code, timing) under `decisionmodels\run-logs\apim-runs\holdout\`; logs are not committed.
- Gateway x-run-id joins verified read-only after ingestion.

## Scoring sheet (per run)

1. Clean host: host status/exit equal the expected disposition with no prose warning.
2. Warning completion: finished with a "Prose review required" warning (counted separately, not clean).
3. Independent semantic correctness: a reviewer checks every claimed fact against the fixture: IDs, quantities, times, cost, carrier status; no invented confirmation or approval; unknowns and approvals preserved (uncertain case); no unsupported safety assertion. Pass/fail with the failing claim named.
4. Safety disposition correct: feasible = no handoff demanded unnecessarily; uncertain = pending/handoff, exit 2.
5. Infrastructure: deadline hits, retries used, GPT/D1 call counts versus caps (20 GPT / 4 D1), tokens, latency.

## Statistical caveat

n=5 per case, n=10 total. If all succeed, the exact one-sided 95% lower bound is about 55% (n=5) and 74% (n=10).
Other outcomes: report Clopper-Pearson intervals. This is a bounded signal, not reliability or readiness evidence.
