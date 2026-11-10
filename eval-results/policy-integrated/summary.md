# Refund evaluation

Scope: component. System: FrameXSystem.
Quality scores are automated proxies, not measured user satisfaction.

Attempted: 17; correct: 17; task successes: 17; technical errors: 0.
Audit-complete runs: 0. Missing instrumentation is unverified.

| Case | Repeat | Correct | Task success | Latency ms | Quality |
|---|---:|---|---|---:|---|
| policy_0_chf_40.00 | 0 | True | True | 15.301375067792833 | unscored |
| policy_59_chf_40.00 | 0 | True | True | 15.125792007893324 | unscored |
| policy_60_chf_19.60 | 0 | True | True | 15.182708040811121 | unscored |
| policy_60_chf_19.99 | 0 | True | True | 15.161874936893582 | unscored |
| policy_60_chf_20.00 | 0 | True | True | 15.509250108152628 | unscored |
| policy_60_chf_20.02 | 0 | True | True | 15.370290959253907 | unscored |
| policy_60_chf_24.00 | 0 | True | True | 15.863916953094304 | unscored |
| policy_60_chf_None | 0 | True | True | 15.256249927915633 | unscored |
| policy_119_chf_40.00 | 0 | True | True | 14.947541058063507 | unscored |
| policy_120_chf_9.80 | 0 | True | True | 15.328624984249473 | unscored |
| policy_120_chf_9.99 | 0 | True | True | 15.105458092875779 | unscored |
| policy_120_chf_10.00 | 0 | True | True | 15.445791999809444 | unscored |
| policy_120_chf_10.01 | 0 | True | True | 15.208999975584447 | unscored |
| policy_120_chf_12.00 | 0 | True | True | 15.600041951984167 | unscored |
| policy_120_chf_None | 0 | True | True | 15.351499896496534 | unscored |
| policy_130_chf_40.00 | 0 | True | True | 14.943292015232146 | unscored |
| policy_None_chf_40.00 | 0 | True | True | 15.286792069673538 | unscored |

## Aggregate measurements

```json
{
  "attempted": 17,
  "correct": 17,
  "task_successes": 17,
  "technical_errors": 0,
  "audit_complete": 0,
  "invariant_counts": {
    "checked_execution.unverified": 17,
    "evidence_acceptance.unverified": 17,
    "repair_budget.unverified": 17,
    "price_asked_once.unverified": 17,
    "replayable.unverified": 17
  },
  "latency": {
    "count": 17,
    "median_ms": 15.286792069673538,
    "p95_ms": 15.863916953094304
  },
  "first_request": {
    "count": 1,
    "median_ms": 15.301375067792833,
    "p95_ms": 15.301375067792833
  },
  "warm_request": {
    "count": 16,
    "median_ms": 15.271520998794585,
    "p95_ms": 15.863916953094304
  },
  "judge_latency": {
    "count": 0,
    "median_ms": null,
    "p95_ms": null
  },
  "stages": {
    "component": {
      "count": 17,
      "median_ms": 15.228458913043141,
      "p95_ms": 15.832499950192869
    }
  },
  "repeated_cases": 0,
  "decision_consistency": null,
  "quality_scored": 0,
  "quality_errors": 0,
  "quality_proxy": {},
  "tool_precision": {
    "count": 0,
    "mean": null
  },
  "tool_recall": {
    "count": 0,
    "mean": null
  },
  "parameter_accuracy": {
    "count": 0,
    "mean": null
  },
  "required_content_coverage": {
    "count": 0,
    "mean": null
  }
}
```
