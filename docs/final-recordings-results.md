# Final recordings: results

Pre-registration: `docs/final-recordings-preregistration.md` (`89241a6`). Source frozen at `a7860e7`
(leg-aware prose checks `3ad0c9c`; narrow coordinator prompt `a7860e7`; offline suite 274 OK).
Live runs went through APIM with Luna and `--debug`; one distinct x-run-id per run, no retries beyond
Package A (none fired), no tuning between runs. All attempts are archived privately (not committed).

| Run | Scenario | Host status | GPT / D1 calls | Wall s | Pre-registered success | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Q01 | quality-hold | pending (exit 2) | 5 / 3 | 558 | Yes | Correct containment/approval handoff; human-input deadline expired (non-interactive). |
| C01 | carrier-delay | pending (exit 2) | 1 / 3 | 314 | No | Correct proposal; D1 validation "Needs revision", so the feasible case paused. |
| C02 | carrier-delay | advisory_complete | 1 / 3 | 17 | Yes | Clean. |
| P01 | production-resequence | pending (exit 2) | 3 / 3 | 434 | No | Correct proposal; validation probability 67% was below routing policy. |
| P02 | production-resequence | advisory_complete | 3 / 3 | 137 | Yes | Clean. |
| O01 | order-pull-forward | advisory_complete | 7 / 3 | 379 | Yes | Clean; split-standard figures match the fixture. |

Eleven of the 20 permitted runs were not needed: each scenario stopped early after its first successful run.
Six runs were made. Gateway x-run-id joins match the client counts for all six (O01 needed ingestion time to
reach 10 of 10). No non-200 responses, no transport retries, no infrastructure failures.

## Selected recordings

Q01, C02, P02, O01. Disclosure counts: quality-hold 1 run, carrier-delay 2, production-resequence 2,
order-pull-forward 1. The viewer must state the count, that the shown run was selected, and link all attempts.

## Warnings and guards

No prose warnings fired in any run, so there were no false positives to report. The two non-successes were
Decision-1 validation outcomes on correct proposals, not guard failures; they are reported separately from
semantic correctness.

## Caveats

- n is very small and scenario-specific (1 to 2 runs each); this shows observed behavior, not reliability.
- Selection after the fact favours the displayed runs. Two of four displayed runs were preceded by an unsuccessful run.
- Quality-hold ended pending because the run is non-interactive; that is the right disposition but not an
  advisory completion.
- Public-candidate replay JSON is built and unpublished; it needs independent review before any site use.
- No readiness claim. Nothing pushed or published.
