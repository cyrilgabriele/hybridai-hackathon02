# Refund evaluation baseline after developer interface

Date: 2026-11-10. Auditor: Cyril. Refreshed after commit `cbe5d3b`.

The pre-merge cases and verification are preserved in `docs/cyril/baselines/`.
The current verification was rerun against the changed rules; its hashes were
not merely copied onto the old results.

The installed client and engine build receipt match the repository pin
`977bb14db288caeb6bf1b253fdb8e25f83ada711`. The Python package reports 0.5.0;
the Rust executable still reports 0.4.4 with an unqualified development commit.
Use the build receipt and installed client source revision to verify alignment.

## Full-snapshot cross-check

Five independently calculated cases were checked against the complete `fx/`
workspace. All five matched FrameX's structured results. Prices below are
synthetic passenger inputs, not observed fares; the base cases use CHF 40.

| Case | Planned departure, 7 November | Destination delay | Expected result |
|---|---|---:|---|
| Interlaken West → Spiez | 17:04 | 0 min | No refund despite cancellation; an alternative arrives on time |
| Spiez → Zürich HB | 17:23 | 66 min | 25%, CHF 10 payout |
| Chiasso → Minusio | 08:05 | 29 min | Missed connection; destination delay still below threshold |
| Bern → Diepflingen | 21:04 | Unmeasurable | Handoff; no actual arrival found within the search bounds |
| Wallisellen → Otelfingen | 03:09 | 149 min | 50%, CHF 20 payout |

These are mechanically verified results for this snapshot, not guarantees about
live services or source-data accuracy. Source timestamps and cancellation records
remain auditable in the frozen evidence.

The verification record is `config/eval/verification.yaml`; full local reports
are `eval-results/after-developer-interface/results.json` and `summary.md`. The snapshot report
uses a 90-second request timeout and 120-second load-request timeout, not latency
acceptance criteria. Initialization took about 8.0 seconds. Per-case component
latency ranged from 7.5 to 25.7 seconds in one growing session; median 22.4 s,
nearest-rank p95 25.7 s over only five samples. This is not chat response latency
and does not establish load performance. An earlier unrestricted run was stopped
before producing results; it is not counted as successful verification.

## Policy-only checks

17 synthetic policy cases: 13 matched, four exposed the agreed rounding
discrepancy. At 25%, prices CHF 19.99 and 20.02 differ in displayed compensation;
at 50%, prices CHF 9.99 and 10.01 differ. Production floors fractional Rappen;
the approved oracle rounds displayed cents half-up after checking the exact
CHF 5 minimum. Entitlement and payout decisions matched on these cases.

The evaluator intentionally reports these four mismatches and exits nonzero.
The passenger-facing `decision` is now `no_refund` when nothing is paid, as in
the incoming pipeline; `refundStatus` remains `entitled` below CHF 5.
It does not change the domain expert's production rules or declare the oracle
to be an independently established legal rounding policy. The original sheet
does not settle this convention; the team should resolve it explicitly.

## Not yet verified

The chat implementation now exists under `src/pipeline/`, but its evaluation
adapter is not connected. Its interpretation,
clarification, repair loop, guarded execution and user-facing claims have not
been tested. Component runs report these audit dimensions as unverified.
The OpenAI judge is implemented and tested with mocked responses; no paid API
calls or actual-user satisfaction measurements were performed.

Additional frozen price/date variants are available but were not all executed
against the full snapshot. Their status remains explicit in the verification
record. Re-run after changing rules, the snapshot, or the system adapter; do not
update expected outcomes merely to match production.
