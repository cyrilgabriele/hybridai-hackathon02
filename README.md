# Swiss rail FrameX knowledge base

A FrameX ontology built from public datasets on [data.sbb.ch](https://data.sbb.ch).
Python maps source records into facts; FrameX rules derive facilities, service
categories, non-stop connections, and dated journeys. Missing evidence remains
unknown under an open world.

## Fact-safe refund assistant (Hackathon 2)

A passenger describes a delayed train journey in their own words. GPT-5 mini reads
the words and phrases the reply. FrameX rules find the train, measure the delay at
the destination from what really ran, and decide the refund. Whatever the rules
cannot settle goes to a person at SBB customer service. The data covers one
operating day, Saturday 7 November 2026, and is already in `fx/`.

```bash
uv sync
sh scripts/install-engine.sh
# Configure .env as shown below when making live model calls.
uv run python src/refund_chat.py        # http://127.0.0.1:7860
```

For live model calls, create or update `.env` in the repository root:

```dotenv
OPENAI_API_KEY=sk-your-key-here
OPENAI_EVAL_MODEL=gpt-5-mini
```

`OPENAI_EVAL_MODEL` selects the evaluation judge; `--judge-model` overrides it.
Keep the API key private. The recorded demo can replay without a key.

The first tab shows the passenger chat next to a live workflow graph: one node per
pipeline step (model, host check, FrameX rules, hand-off), lit as data passes through,
with an inspector listing exactly what was sent and returned. A step log and the
rules' proof sit below. The second tab is the customer-service desk.

| Pattern | Where it runs |
|---|---|
| P3 Model as Translator | words become a checked `RefundCase` request ([slots.py](src/pipeline/slots.py), [knowledge.py](src/pipeline/knowledge.py)); the rules' decision becomes words |
| P1 Model as Sensor | every slot carries the passenger's quote; the host accepts it only if the quote occurs in the message |
| P6 Critique and Repair | failed checks go back with a fixed reason, one repair round for slots and replies; then the passenger is asked or fixed wording is used |
| P12 Model Selects, Rules Write | the model picks train identifiers from the rules' list and writes words around values it never sees ([reply.py](src/pipeline/reply.py)) |
| P7 Division by Competence | the rules decide what they cover; the rest goes to a person with the model's note ([competence_gate.fx](src/pipeline/programs/competence_gate.fx), [handoff.py](src/pipeline/handoff.py)) |

The policy is in [47-refund-policy.fx](src/ontology/ontology/47-refund-policy.fx) and
the language contract in [refund-chat.md](docs/refund-chat.md). Decisions are in
[docs/adrs](docs/adrs/).

**Tools declared for the hackathon.** Coding agent: Claude Code with Claude Opus 5.5.
Language model inside the system: GPT-5 mini through the official OpenAI client
([llm.py](src/pipeline/llm.py)).

**Demo without a key.** `model-answers/` holds the recorded answers of the
conversations in [record_demo.py](scripts/record_demo.py). The same messages replay
in the chat and with `uv run python scripts/record_demo.py`; any other message needs
a key.

**Limits.** A journey has at most one change, as in `46-refunds.fx`; the train is
searched within 30 minutes of the stated time, with a 5-minute transfer allowance.
A decision takes about 15 seconds and runs one at a time.

## Evaluate the refund assistant

```bash
# Fresh GPT-5 mini assistant calls and GPT-5 mini quality judging; requires the key.
uv run python -m eval run --cases config/eval/snapshot.yaml \
  --adapter pipeline.eval_adapter:create --judge openai --judge-model gpt-5-mini \
  --output eval-results/chat
uv run python -m eval run --cases config/eval/dialogue.yaml \
  --adapter pipeline.eval_adapter:create --judge openai --judge-model gpt-5-mini \
  --output eval-results/dialogue
```

Reports include policy correctness, communication, actual audit events, token
usage and measured latency. See [evaluation](docs/evaluation.md) for offline
component checks, recorded replay, fault fixtures and limitations.

## Quick start

Requires Python 3.10+, [uv](https://docs.astral.sh/uv/), and Rust
([rustup](https://rustup.rs)) to build the FrameX engine. Run commands from the
repository root:

```bash
uv sync
sh scripts/install-engine.sh
uv run python src/main.py --init
uv run python src/main.py --repl
```

`uv sync` installs the FrameX Python client from
[framex-core](https://gitlab.com/ds-unisg/framex-core). The install script builds
the engine from the same commit into `.venv/bin/framex`, so no global install is
needed. To move to a newer FrameX, change the `rev` in `pyproject.toml`
(`[tool.uv.sources]`), then rerun both commands.

Initialization downloads source data and writes the knowledge base to `fx/`.
The REPL loads it once and reuses the session. For a single query:

```bash
uv run python src/main.py --query '?- sp_8509000[hasWifi -> ?W].'
```

Run local tests with `uv run pytest -q`. Full-snapshot checks are opt-in;
see the development guide for setup.

## Documentation

| Guide | Contents |
|---|---|
| [Usage](docs/usage.md) | Builds, queries, REPL, journeys, and Python sessions |
| [Ontology](docs/ontology.md) | Semantics, identities, mappings, and extensions |
| [Data](docs/data.md) | Dataset discovery, API options, and source-data quirks |
| [Development](docs/development.md) | Architecture, loading, publication, and testing |
| [Pattern lookup](docs/patterns.md) | Targeted links to the ten Hybrid AI reference implementations |
| [Course lookup](docs/course-lookup.md) | VL04/VL05 page index, H1 lessons, and H2 preparation gaps |
| [Refund chat](docs/refund-chat.md) | Language contract of the refund assistant |
| [Refund evaluation](docs/evaluation.md) | Snapshot cases, independent policy checks, adapters, automated quality judging and performance reports |
| [FrameX core](https://gitlab.com/ds-unisg/framex-core) | Engine and Python client sources |

## Repository layout

| Path | Purpose |
|---|---|
| `src/main.py` | CLI entry point |
| `src/cli/` | Commands, REPL, progress, and answer formatting |
| `src/data/` | SBB API access |
| `src/ontology/` | Rules, mappings, identities, and fact generation |
| `src/runtime/` | Engine sessions, source loading, and validation |
| `src/refund_chat.py` | Starts the refund assistant |
| `src/pipeline/` | Model client, slot checks, per-case worlds, control flow, replies, hand-off |
| `src/ui/` | Gradio chat, workflow view, and customer-service desk |
| `src/eval/` | Evaluation ports, metrics, adapters, and YAML config loaders |
| `config/eval/` | Policy, dialogue, snapshot cases and verification records |
| `model-answers/` | Recorded GPT-5 mini answers for replay |
| `tests/` | Regression tests and opt-in snapshot checks |
| `docs/` | User and developer guides |
| `scripts/install-engine.sh` | Builds the FrameX engine into `.venv/bin` |
| `scripts/record_demo.py` | Records or replays the demo conversations |
