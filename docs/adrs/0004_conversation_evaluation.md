# 4. Evaluate the production conversation through structured events

Date: 2026-11-10

## Status

Accepted

## Context

Component evaluation cannot certify slot extraction, filtered case worlds, reply
checks or passenger-facing behavior. Display-oriented workflow text is not a
reliable machine-readable audit trail.

## Decision

Implement the conversation port in `pipeline.eval_adapter`, invoking the same
assistant as the UI. Isolate conversation and desk state per attempt while
sharing read-only source indexes. Expected answers, oracle witnesses, case IDs
and fixture-selected train IDs never become model inputs.

Record structured events where production checks and operations occur, including
quote provenance, checked execution, rule bindings, acceptance evidence and
separate extraction/phrasing repair scopes. Preserve raw arrival epochs and
entitlement/payout bindings in production results. Technical failures retain
the passenger turn for audit evidence and expose only sanitized error types.

Use explicitly declared dependency fault fixtures for adversarial scenarios.
Fixture-controlled cases remain labeled and do not establish live engine or
model performance. Scripted assistant messages are fixture context; actual
responses are retained separately and drive the real conversation state.

Default conversation evaluation to fresh GPT-5 mini calls and a separate recording
store. Explicit replay mode never calls the provider when a recording is absent.
Report original model usage, source/snapshot hashes and transcripts. Exclude
recorded or injected model runs from live-performance aggregates. Quality
judging remains explicit and independent; the integration verification uses
GPT-5 mini for both assistant and judge.

## Alternatives considered

Parsing workflow titles into audit events could invent ordering or approvals.
Copying the assistant into evaluation would test another implementation.
Sending hidden fixture train IDs would bypass real journey identification.

## Consequences

Production modules expose audit data without importing evaluation types. Ordinary
tests exercise real rules with controlled model responses; live runs separately
verify provider behavior. Reports distinguish correctness, task success and
invariant coverage; early clarifications can legitimately lack execution coverage.
See [evaluation](../evaluation.md) for commands and verification evidence.
