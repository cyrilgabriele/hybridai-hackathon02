# 3. Independent refund evaluation through ports

Date: 2026-11-10

## Status

Accepted

## Context

The refund chat and its evaluator develop independently. The auditor needs reproducible checks of
policy decisions, journey evidence, guarded execution, communication and latency
without coupling evaluation to the eventual chat implementation.

## Decision

Use a hexagonal evaluation package under `src/eval`. The core owns scenarios,
independent expectations, deterministic metrics and reports. System and judge
ports isolate FrameX, recorded runs, the chat and OpenAI. Expected
answers and oracle evidence never cross the system port.

Case definitions live in `config/eval/*.yaml`. Mirrored modules under
`src/eval/cases/` load strict frozen document models; shared case records remain
compatible with the evaluator's ports. Safe YAML loading rejects duplicate keys
and unknown document fields. Runtime reports remain JSON/Markdown. Config files
ship as wheel data rather than being embedded in the Python source package.

Freeze journey scenarios from the 7 November snapshot with file hashes and
event witnesses. An imperative oracle enumerates direct and one-change paths;
FrameX cross-checks rather than generates the expected answers. Keep synthetic
threshold and fault cases when real data cannot cover a boundary.

Use the approved exact-amount payout test and half-up cent display rounding in
the oracle. Production now uses the same display rounding and compares the exact share
against the payout minimum. Earlier floor-rounding results remain archived.

Deterministic correctness and trace checks remain separate from the OpenAI
quality judge. Missing instrumentation is unverified. Judge failures are
unscored, and scores are quality proxies rather than measured satisfaction.
Performance is measured and reported without invented acceptance thresholds.

## Alternatives

Generating expected answers with production rules would conceal shared errors.
Direct coupling to chat internals would weaken the independent evaluation boundary. Human scoring is
outside the agreed scope. A model judge alone cannot establish refund correctness.

The production pipeline's no-payout response is `no_refund`; entitlement remains
a separate field. Extraction and phrasing have separate one-repair budgets.

## Consequences

Adapters must expose structured decisions, evidence and traces. Snapshot-backed
runs are explicit and can be expensive; ordinary tests use local fixtures and
mocked provider responses. The supplied policy is a hackathon specification,
not a live passenger-rights service. See `docs/evaluation.md` for commands,
contracts, arithmetic assumptions and limitations.
