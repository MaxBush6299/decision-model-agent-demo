# Multi-option rerun results (pre-registration `5757ecb`; frozen source merge `6db410b`)

6 sequential live runs via APIM, Luna, `--debug`, distinct x-run-id. No retries, tuning or replacement; no infrastructure/auth/routing failure, so none stopped early. Raw logs are archived outside the repo (`decisionmodels\run-logs\apim-runs\multi-option-rerun\`). No readiness claim.

| Run | x-run-id | Specialists | Host outcome / exit | Final D1 validation | Prose warnings | GPT/D1 calls (gateway, all 200) | GPT tokens | Time |
|---|---|---|---|---|---|---|---|---|
| O01 | c6ab8241 | 3 | pending / 2 | Needs revision 78.8% | 1 (prose.pickup) | 7/3 | 28,787 | 679s |
| O02 | 94d593f6 | 3 | advisory complete / 0 | Addresses 96.0% | 0 | 7/3 | 27,936 | 377s |
| O03 | 4b665e8b | 3 | pending / 2 | Addresses 91.1% | 1 (prose.booking) | 7/3 | 28,192 | 379s |
| P01 | 6ac298e5 | 1 (production) | pending / 2 | Needs revision 78.3% | 0 | 3/3 | 12,864 | 441s |
| P02 | d8047baf | 1 | pending / 2 | Needs revision 76.2% | 0 | 3/3 | 12,511 | 435s |
| P03 | 068d49e0 | 1 | pending / 2 | Addresses 97.6% | 0 | 3/3 | 12,575 | 437s |

## Scoring (pre-registered sheet)
- Clean host (exit 0, no warning): 1/6 (O02). Order 1/3, production 0/3.
- Warning completion: 2/6 (O01, O03), both pending solely because of "Prose review required".
- Package C warnings: 2 fired in 6 runs, both FALSE positives by reading against the fixture:
  - O01 `prose.pickup`: claim "Friday 09:00-10:00 window is supported by derived arrival Friday 09:30" is a correct arrival statement (fixture arrival 09:30); the guard compared it to the Thursday 18:30 pickup.
  - O03 `prose.booking`: "Friday 09:00 ... for split-standard" is the genuine booking cutoff of the second split leg (fixture shipment cutoff 2026-10-16T09:00); the guard compared it to the first leg cutoff (Thu 16:30).
  Both mistake multi-leg/derived-time mentions for a wrong single-leg value. Before Package C these would have been fatal; now they are visible warnings, but still cost host completion. No true positives observed.
- Semantic review (all six read against the fixture): no incorrect fact found in O01-O03 or P01-P03 final output. P03 additionally correctly preserved a conflicting Production headroom claim (P3 greater headroom) against the derived figures (P2 60 min vs P3 50 min), which is why it ended pending (conflicting evidence), not a defect.
- Fully reviewed pass (clean host AND semantic pass): 1/6.
- Why production was pending 3/3: Decision-1 proposal validation returned "Needs revision" in 2 of 3 on semantically correct recommendations (variance/over-conservatism) and a preserved conflict in the third. All were safe dispositions, not unsafe claims.

## Infrastructure
Longest single request 15.8s vs 120s Luna deadline; no Package A retries; no non-200; caps never approached (max 7/20 GPT, 3/4 D1). Gateway x-run-id joins match client counts exactly. Wall times are dominated by local 10 RPM pacing and the human-input deadline wait.

## Comparison and caveat
Earlier batch 25-29: 4/5 host, 3/5 fully reviewed; this batch 1/6 clean host (3/6 if warning completions are counted as host-completed without a fatal error, as the pre-Package-C runs would not have), 1/6 fully reviewed. Different scenario mix (25-29 used the prior source and fatal guards) and tiny n; the difference is not statistically separable (Clopper-Pearson for 1/6 is about 0.4%-64%). The observed pattern is that false-positive prose warnings and Decision-1 validation variance, rather than unsafe content, drive non-clean outcomes. n=3 per scenario; this is not reliability or readiness evidence.
