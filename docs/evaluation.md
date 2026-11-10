# Refund evaluation

The auditor's evaluator is independent of the refund implementation. It uses
the supplied Sheet 2 policy, the [chat contract](refund-chat.md), and the
[auditor mandate](cyril/mandate.md). No refund chat is implemented by this package.

## Run

```sh
uv sync
sh scripts/install-engine.sh

# Fast policy-only component evaluation. Fractional-cent cases expose the
# production rounding discrepancy below, so a nonzero result is expected.
uv run python -m eval run --cases config/eval/policy.yaml --framex \
  --output eval-results/policy

# Freeze independently enumerated cases from the existing snapshot; no download.
uv run python -m eval discover --workspace fx --limit 250 \
  --output eval-results/discovered.yaml

# Cross-check the committed cases against the FULL snapshot, not a reduced base.
uv run python -m eval run --cases config/eval/snapshot.yaml --framex \
  --workspace fx --output eval-results/snapshot

# Conversation evaluation: supply an adapter for the implemented pipeline.
uv run python -m eval run --cases config/eval/snapshot.yaml \
  --adapter pipeline.eval_adapter:create --repeats 3 --output eval-results/chat

# Evaluate recorded attempts without timing JSON replay as system performance.
uv run python -m eval run --cases config/eval/snapshot.yaml \
  --saved eval-results/chat/results.json --output eval-results/replay
```

The incoming `src/pipeline/assistant.py` implements the chat with
`Assistant.handle(Conversation, text)`. `pipeline.eval_adapter:create` remains an
interface example, not an existing module: its adapter must translate that
conversation state and actual traces into the contract below. Component runs
do not certify the pipeline's filtered-world selection or user-facing behavior.
Use repeatable `--case CASE_ID` arguments to select representative cases. The
FrameX adapter accepts `--timeout` and `--load-timeout` in seconds; these bound
execution and do not define performance acceptance thresholds. Progress is
printed to stderr, with one result line per attempted case.
The package is included in the project's wheel, with YAML configs installed as
data under `share/hybridai-h1/config/eval` in the installation prefix. Commands
below assume the repository root; from another directory pass explicit config
paths. Exit codes: 0 means all expected
decisions/facts match, 1 means at least one mismatch or unexpected system error,
2 means invalid configuration or an evaluation startup failure. Inspect task
success and audit coverage as well as correctness; an exit code alone does not
certify the agent's guardrails.

`results.json` contains each attempted run, expected values, actual observations,
scores and exceptions by type. `summary.md` shows the counts and measurements.
Output directories are ignored by Git. Full snapshot runs can take substantially
longer than unit tests. They reuse a session, but initial closure and each request
can still be expensive. No production timeout is converted to unknown or denial.

## Hexagonal contract

Core modules own cases, the policy oracle, snapshot enumeration, metrics and
reports. `adapters/` owns FrameX, saved runs and the direct OpenAI judge.

Implement the `SystemPort` in `eval.contracts`:

```python
from eval.contracts import Observation, SystemInput

class RefundSystemAdapter:
    scope = "conversation"

    def run(self, case: SystemInput) -> Observation:
        # Send only case.messages and necessary case.request fields to your
        # system. Route scenario/fault settings through a test-only boundary.
        # Return actual outputs and captured events; never fabricate evidence.
        raise NotImplementedError("Connect the refund implementation here")

    def close(self) -> None:
        pass

def create():
    return RefundSystemAdapter()
```

`SystemInput` exposes `id`, `request`, `messages` and `snapshot` hashes. It has no
expected answers, oracle evidence or scoring instructions. Treat the ID as an
opaque correlation key, never as model input: case names can reveal categories.
Canonical event IDs are fixture controls for components; the conversational
system must establish the journey from passenger messages, not receive a hidden
oracle-selected train as the model's answer. Scripted assistant messages in the
dialogue corpus define an initial context, not expected generated replies.

`Observation` fields:

| Field | Meaning |
|---|---|
| `decision` | `refund`, `no_refund`, `handoff`, `question`, or technical `error` |
| `reply` | Actual passenger-facing response; empty for component-only runs |
| `facts` | Actual bindings: `refundStatus`, `refundPercent`, `refundCHF` (two-decimal string or null), `paidOut`, `delayMinutes`, and available arrival epochs; dialogue scenarios may expose `critiqueReason` and resolved station IDs |
| `events` | Ordered actual extraction, validation, execution, acceptance and repair events |
| `coverage` | Instrumented dimensions, e.g. `checked_execution`, `evidence_acceptance`, `repair_budget`; absence remains unverified |
| `stage_ms` | Available stage durations in milliseconds; never guessed |
| `usage` | Actual model token usage, if available |
| `metadata` | Model/version, timestamp, receipt ID, evidence anchors, and relevant system configuration |
| `error` | Sanitized technical failure, never a business verdict |

Trace conventions:

- `validate`: `call_id`, `name`, `arguments`, `approved: true/false`.
- `execute`: matching `call_id`, `name`, `arguments`. Approval must precede the
  execution and match its actual arguments, not merely share a call ID.
- `accept`: nonempty `evidence` list referencing actual anchors in
  `metadata.evidence`. Anchor examples are source-event bindings and checked
  passenger quotes. Existence of a trace is not a proof that the source is true.
- `slot`: `accepted`, `quote`, `message_index`; accepted quotes must occur in the
  corresponding message, case-insensitively. Quote occurrence alone does not
  establish semantic correctness; expected arguments and judge evidence checks
  provide separate checks.
- `repair`: one event per actual retry, with a `scope_id` per extraction or
  phrasing operation (including its turn). More than one retry within the same
  scope violates the chat contract; separate stages may each repair once.
  Events without a scope share one conservative legacy budget.
- `ask`: use `slot: "price"` for price requests; more than one violates the
  ask-once contract. Declare `price_asked_once` in coverage when instrumented.

Replayability requires `metadata.timestamp`, `system_version`, `model` and
`receipt_id`. The report retains the input case and observations. Do not put API
keys in metadata or traces. The evaluator records exception types rather than
provider error bodies to avoid credential leakage.

## Corpora and independent expectations

Scenario definitions live under `config/eval/`. Each YAML document declares a
`kind` and `version`; its model and loader mirror the filename under
`src/eval/cases/`:

| Config | Model and loader |
|---|---|
| `config/eval/policy.yaml` | `eval.cases.policy.PolicyCases`, `load()` |
| `config/eval/dialogue.yaml` | `eval.cases.dialogue.DialogueCases`, `load()` |
| `config/eval/snapshot.yaml` | `eval.cases.snapshot.SnapshotCases`, `load()` |
| `config/eval/verification.yaml` | `eval.cases.verification.Verification`, `load()` |

Use `eval.cases.load_cases(path)` to load a runnable corpus, or a mirrored
module's `load(path)` for the full document. `eval.cases.models.Case` is the
shared case record, also exported through `eval.contracts` for existing adapters.
Document models are frozen and reject unknown fields; case IDs and YAML keys
must be unique. Quote monetary values such as `'19.60'` and `'4.90'` to preserve
exact decimal strings. Operating dates stay strings, including unquoted ISO
dates. Discovery writes a validated YAML config; recorded results stay JSON.

- `policy.yaml`: synthetic measured-delay inputs at 0/59/60/119/120/130 minutes,
  missing evidence, missing price, and payout boundaries. These are **not** real
  journey claims.
- `snapshot.yaml`: frozen cases calculated from actual event facts and names,
  including cancellation, missed connection, 0%/25%/50%, and missing actual
  journeys. Ticket prices are explicit synthetic passenger inputs, not observed
  fares. SHA-256 hashes identify the full workspace, including rules and manifest.
- `dialogue.yaml`: explicit clarification, fabricated-extraction, injection,
  correction, and failure scenarios. The system adapter must implement the named
  test setup/faults. These are not runnable through the FrameX component adapter.

Discovery searches the full source-fact graph for the earliest scheduled and
earliest REAL arrival, with at most one change. It does not use production
FrameX results as its expected values. Route witnesses and full timestamps are
retained. Snapshot-day membership, five-minute transfers, one-hour change waits,
three-hour initial boarding waits and a seven-hour total search horizon are
explicit. These are the current bounded search contract, not a guarantee about
all possible railway journeys. Midnight timestamps retain their date.

Both the independent oracle and the incoming rules reject planned connections
that arrive before (or at) departure; the oracle also rejects individual
backwards-time legs. This prevents a shared trip reference from creating a
phantom connection.

The independent oracle permits a one-change route even if the selected train
also reaches the destination directly. The production rules currently suppress
that planned search when a direct journey exists. Disagreement must be audited,
not resolved by changing the expected answer to match production.

Candidates must also survive the ±30-minute departure window and dominance
check. Each category is frozen only when found; missing coverage is recorded in
the discovery document. Running FrameX cross-checks the expectations; it does
not retroactively make every case correct. No reduced fixture is assumed
equivalent to the full dataset.

The committed `verification.yaml` records the five representative cases actually
cross-checked against the full snapshot, the case-document hash and unexecuted
variants. See the [initial audit baseline](cyril/evaluation-baseline.md). It does
not claim that every frozen case or the conversation system was tested. The
pre-interface snapshot and verification are archived under `docs/cyril/baselines/`.

### Decision labels, money assumption and known discrepancy

The incoming pipeline uses `decision: no_refund` for no payout, including a
compensation amount below CHF 5. The evaluator follows this response label
while independently checking that `refundStatus` is still `entitled`, the
percentage is unchanged, and `paidOut` is false. No payout is not denial of
entitlement.

The supplied sheet does not specify fractional-cent rounding. The approved
oracle uses Decimal, compares the **unrounded** compensation with CHF 5, and
then rounds the displayed amount half-up to cents. Production
`47-refund-policy.fx` floors fractional Rappen. For example, at 25%, CHF 20.02
produces displayed CHF 5.01 in the oracle and CHF 5.00 in production. CHF 19.99
displays CHF 5.00 but remains below the exact payout minimum. The evaluator
deliberately exposes this discrepancy; production rules are not modified.

## Automatic quality judge

```sh
uv run python -m eval run --cases config/eval/snapshot.yaml \
  --saved eval-results/chat/results.json --judge openai \
  --judge-model "$OPENAI_EVAL_MODEL" --output eval-results/judged
```

Use `OPENAI_API_KEY` in the environment or root `.env`; existing environment
values take precedence. Specify `--judge-model` or `OPENAI_EVAL_MODEL`. No model
is silently selected. To reuse the team's OpenAI client, pass
`--client-factory module:create_client`. The injected client must expose the
official SDK's `responses.create` interface. The built-in client has a 60-second
timeout and one SDK retry. No API calls occur unless judging is explicitly enabled.

The judge rates relevance, clarity, coherence, evidence fidelity and actionability
on anchored 1–5 scales, with a reason and an exact response excerpt per rating.
Structured outputs are validated locally, including excerpt occurrence. Refusal,
incomplete output, invalid scores and provider failures are reported as unscored
judge errors. No judge score changes deterministic policy correctness.

These are automated **quality proxies**, not CSAT or actual user satisfaction.
No human scoring or simulated customer is required. There is no calibrated
quality pass threshold. Judge limitations include model bias and imperfect
semantic assessment, even with valid JSON and excerpts.

Sources: Michael Albada, *Building Applications with AI Agents*, Chapter 9,
“Validation and Measurement,” especially printed pp. 210–219 (tool metrics,
holistic evaluation, consistency, coherence and hallucination); Chapter 2,
p. 36 distinguishes actual-user feedback. Provider integration follows the
[OpenAI Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).

## Measurements and checks

Every attempted case remains in the correctness denominator, including technical
errors. Missing expected tool annotations produce null metrics with count zero,
not perfect scores. Tool metrics count duplicate calls; argument matching is
one-to-one. Communication checks cover required values, not general semantic
truth. Guardrail verification has passed/failed/unverified states. Successful
task outcomes and complete audit coverage are separate dimensions.

Repeated-run consistency compares structured decisions/facts, not identical
prose. Latencies use a monotonic clock and nearest-rank p95, with sample counts.
Initialization, first request, subsequent requests, available stage timings and
judge time are separate. Replayed runs retain only original reported latency;
JSON replay duration is never an agent-performance measurement. No concurrency
or load test is implied by sequential repetitions. No monetary cost is inferred
from token counts or assumed prices.

```sh
uv run pytest tests/eval -q
uv run ruff check
uv run ty check
uv run pytest -q
```

Normal tests use tiny fixtures and mocked judge responses, not paid API calls or
the full snapshot. Real-system tests require a system adapter; the component
adapter cannot assess passenger-facing communication or the agent's guardrails.
