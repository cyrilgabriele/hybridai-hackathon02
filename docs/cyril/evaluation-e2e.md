# End-to-end evaluation verification

Executed on 10 November 2026 using GPT-5 mini for both assistant and independent quality judge.

| Run | Correct / attempted | Task successes | Quality scored |
|---|---:|---:|---:|
| Live snapshot conversations | 17 / 17 | 17 | 17 |
| Dialogue and fault scenarios | 9 / 9 | 9 | 7 |
| Final scripted-context recheck | 1 / 1 | 1 | 1 |
| Independent policy component | 17 / 17 | 17 | — |
| Full-workspace representative component | 7 / 7 | 7 | — |

Live snapshot response median: 16.6 s; nearest-rank p95: 25.2 s (17 sequential requests). Judge time is separate.

All 17 snapshot runs passed every instrumented invariant. Dialogue tests include two expected technical errors. Early clarifications and rejected proposals correctly leave execution/acceptance unverified when no corresponding operation occurs. Injected/recorded model responses are excluded from live-performance aggregates.

All 24 eligible replies from the two corpus runs received quality scores, with zero judge errors. The final scripted-context recheck was also scored successfully. These are automated proxies, with no calibrated pass threshold or claim of actual user satisfaction.

The full snapshot run verified cancellation, 0%/25%/50%, missing actual arrival, changed transfer route and missed connection against independent expectations. The committed verification config records these seven component checks. Fractional-cent variants were exercised through the production assistant in the live corpus and through isolated policy rules; they are not claimed as additional full-workspace component checks.

Independent regeneration preserved every expected outcome, witness and passenger message; only snapshot rule hashes and generation metadata changed. Pre-integration verification and cases remain in `baselines/pre-e2e/`.

Reports (local, ignored by Git):

- `eval-results/e2e-snapshot/{results.json,summary.md}` — live corpus and GPT-5 mini judging.
- `eval-results/e2e-dialogue/{results.json,summary.md}` — dialogue/fault corpus and judging.
- `eval-results/e2e-context-final/{results.json,summary.md}` — final context-aware correction recheck.
- `eval-results/e2e-full-component/{results.json,summary.md}` — final snapshot full-workspace cross-check.
- `eval-results/policy-integrated/{results.json,summary.md}` — independent policy boundaries.

Each JSON records the attempted inputs, actual observations and scores. Conversation reports retain source/snapshot hashes, model identity, measured usage, timestamps, receipts and actual audit evidence. The snapshot live run preceded final provenance/context refinements; the context-specific live recheck and final regression suite verify those refinements. No repeated-run consistency or load testing is claimed.
