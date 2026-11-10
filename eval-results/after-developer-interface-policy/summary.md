# Refund evaluation

Scope: component. System: FrameXSystem.
Quality scores are automated proxies, not measured user satisfaction.

Attempted: 17; correct: 13; task successes: 13; technical errors: 0.
Audit-complete runs: 0. Missing instrumentation is unverified.

| Case | Repeat | Correct | Task success | Latency ms | Quality |
|---|---:|---|---|---:|---|
| policy_0_chf_40.00 | 0 | True | True | 16.163457999937236 | unscored |
| policy_59_chf_40.00 | 0 | True | True | 16.053750063292682 | unscored |
| policy_60_chf_19.60 | 0 | True | True | 15.957958996295929 | unscored |
| policy_60_chf_19.99 | 0 | False | False | 16.012333100661635 | unscored |
| policy_60_chf_20.00 | 0 | True | True | 15.851917094551027 | unscored |
| policy_60_chf_20.02 | 0 | False | False | 15.946915955282748 | unscored |
| policy_60_chf_24.00 | 0 | True | True | 15.037958044558764 | unscored |
| policy_60_chf_None | 0 | True | True | 15.254291007295251 | unscored |
| policy_119_chf_40.00 | 0 | True | True | 15.301709063351154 | unscored |
| policy_120_chf_9.80 | 0 | True | True | 15.323834028095007 | unscored |
| policy_120_chf_9.99 | 0 | False | False | 15.539875021204352 | unscored |
| policy_120_chf_10.00 | 0 | True | True | 15.473666950128973 | unscored |
| policy_120_chf_10.01 | 0 | False | False | 31.27937496174127 | unscored |
| policy_120_chf_12.00 | 0 | True | True | 19.054583040997386 | unscored |
| policy_120_chf_None | 0 | True | True | 15.731458086520433 | unscored |
| policy_130_chf_40.00 | 0 | True | True | 16.18179096840322 | unscored |
| policy_None_chf_40.00 | 0 | True | True | 16.087291995063424 | unscored |

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
    "median_ms": 15.946915955282748,
    "p95_ms": 31.27937496174127
  },
  "first_request": {
    "count": 1,
    "median_ms": 16.163457999937236,
    "p95_ms": 16.163457999937236
  },
  "warm_request": {
    "count": 16,
    "median_ms": 15.899416524916887,
    "p95_ms": 31.27937496174127
  },
  "judge_latency": {
    "count": 0,
    "median_ms": null,
    "p95_ms": null
  },
  "stages": {
    "component": {
      "count": 17,
      "median_ms": 15.912375063635409,
      "p95_ms": 31.21820802334696
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
