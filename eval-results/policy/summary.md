# Refund evaluation

Scope: component. System: FrameXSystem.
Quality scores are automated proxies, not measured user satisfaction.

Attempted: 17; correct: 13; task successes: 13; technical errors: 0.
Audit-complete runs: 0. Missing instrumentation is unverified.

| Case | Repeat | Correct | Task success | Latency ms | Quality |
|---|---:|---|---|---:|---|
| policy_0_chf_40.00 | 0 | True | True | 16.496750060468912 | unscored |
| policy_59_chf_40.00 | 0 | True | True | 14.994459110312164 | unscored |
| policy_60_chf_19.60 | 0 | True | True | 15.845625079236925 | unscored |
| policy_60_chf_19.99 | 0 | False | False | 15.660415985621512 | unscored |
| policy_60_chf_20.00 | 0 | True | True | 15.43308305554092 | unscored |
| policy_60_chf_20.02 | 0 | False | False | 17.327083041891456 | unscored |
| policy_60_chf_24.00 | 0 | True | True | 21.278291940689087 | unscored |
| policy_60_chf_None | 0 | True | True | 15.472499886527658 | unscored |
| policy_119_chf_40.00 | 0 | True | True | 15.81058301962912 | unscored |
| policy_120_chf_9.80 | 0 | True | True | 15.41754207573831 | unscored |
| policy_120_chf_9.99 | 0 | False | False | 15.250583994202316 | unscored |
| policy_120_chf_10.00 | 0 | True | True | 15.414000023156404 | unscored |
| policy_120_chf_10.01 | 0 | False | False | 15.669959015212953 | unscored |
| policy_120_chf_12.00 | 0 | True | True | 15.644790953956544 | unscored |
| policy_120_chf_None | 0 | True | True | 14.931125100702047 | unscored |
| policy_130_chf_40.00 | 0 | True | True | 15.252624987624586 | unscored |
| policy_None_chf_40.00 | 0 | True | True | 15.279874904081225 | unscored |

## Aggregate measurements

```json
{
  "attempted": 17,
  "correct": 13,
  "task_successes": 13,
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
    "median_ms": 15.472499886527658,
    "p95_ms": 21.278291940689087
  },
  "first_request": {
    "count": 1,
    "median_ms": 16.496750060468912,
    "p95_ms": 16.496750060468912
  },
  "warm_request": {
    "count": 16,
    "median_ms": 15.452791471034288,
    "p95_ms": 21.278291940689087
  },
  "judge_latency": {
    "count": 0,
    "median_ms": null,
    "p95_ms": null
  },
  "stages": {
    "component": {
      "count": 17,
      "median_ms": 15.438959002494812,
      "p95_ms": 21.234584040939808
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
