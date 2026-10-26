# Multi-option rerun pre-registration (committed before any live run)

Frozen source: the commit containing this file's parent merge `6db410b` (v2 line = v2-hardening-offline merged; Packages A, B-data, C, D, APIM profile). Only docs change after this commit.

## Protocol
- 6 sequential runs: 3 x `order-pull-forward`, then 3 x `production-resequence`.
- `python -m decision_v2.cli --example <case> --llm-profile gpt-6-luna --debug`, via APIM, distinct x-run-id (v2 run id).
- No retries beyond the Package A transport rule; no code/prompt/schema/config changes before, between or after runs.
- Stop only on infrastructure/auth/routing failure; model failures do not stop the batch. Archive all attempts outside the repo (`decisionmodels\run-logs\apim-runs\multi-option-rerun\`). Gateway x-run-id joins verified read-only.

## Scoring (fixed before the first run)
1. Clean host: host exit 0/`advisory_complete` (or the scenario's expected handoff) with no prose warning and no fatal error.
2. Warning completion: finished pending/exit 2 solely due to "Prose review required". Each warning is classified TRUE positive (the quoted claim is unsupported by the fixture) or FALSE positive (supported or non-claim), by independent reading against the fixture.
3. Semantic review: every factual claim in the final output (IDs, quantities, times, costs, option comparison, unknowns/approvals) is checked against the fixture; pass/fail naming the failing claim. "Fully reviewed pass" = clean host AND semantic pass.
4. Fail-closed errors (exit 1) are reported by guard/field; infrastructure: deadline hits, retries, call caps, tokens, latency.

## Comparison and caveat
Compared descriptively with runs 25-29 (4/5 host, 3/5 fully reviewed) and the APIM recordings. n=3 per scenario, n=6 total: Clopper-Pearson intervals are wide; no reliability or readiness claim.
