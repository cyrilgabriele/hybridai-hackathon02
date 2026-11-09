# H2 course lookup

Read this index, select one concept, then open only the indicated PDF pages or
source files. Page numbers are PDF page numbers. This maps available teaching
material to the starter repository; it is not an H2 assignment or grading rubric.
The specific H2 brief was not found among the local course files.

## Sources

| Source | Use |
|---|---|
| [VL04: Rules and Language Models](../../01_lectures/VL04_Rules_and_Language_Models.pdf) | Why couple models and rules; control and authority; both directions of tool use. |
| [VL05: Agentic AI](../../01_lectures/VL05_Agentic_AI.pdf) | Guarded loops, checked requests, evidence-preserving answers, and governed memory. |
| [Pattern decision sheet](../../02_exercises/03_week/HybridAIPatternDecision.pdf) | One-page selection tree for P1–P11 and five composition invariants. |
| [Pattern implementation lookup](patterns.md) | Direct links to P1–P10 Python examples, shared helpers, and P11 lecture material. |
| [EvoSym H1 overview](../../EvoSym/README.md) | Prior solution: ingestion, ontology, rules, 18 TA queries, explanations, and independent expected answers. |
| [EvoSym H1 report](../../EvoSym/report/main.tex) | Evaluation and limitations; search `Evaluation`, `Counterfactual`, or `Discussion`. |

## Concept → lecture → implementation

| Need | Read first | Pattern | Existing entry here / remaining work |
|---|---|---|---|
| Decide whether a hybrid is justified | VL04 pp. 11–14, 37–40 | Selection sheet | Identify the task's need for both language handling and executable rules before adding an LLM. |
| Assign control and authority | VL04 p. 23; VL05 pp. 11–13 | All | Name the next-step controller, boundary data, final authority, and state lifetime. No agent controller exists here yet. |
| Extract facts with evidence | VL04 pp. 28–33 | P1 | [`emit.py`](../src/ontology/emit.py) renders facts; add proposal validation and quote/source checks before accepting model output. |
| Draft or critique rules | VL04 pattern map; [P2/P9 examples](patterns.md) | P2, P6, P9 | Existing `.fx` rules and tests provide a checker; generated rules need isolated checking and review before adoption. |
| Translate language to checked requests | VL05 pp. 22–25 | P3, P4 | [`Session.ask`](../src/runtime/session.py) accepts raw queries. Add a closed operation contract and adapter that builds queries from validated arguments. |
| Ground mentions and clarify ambiguity | VL05 pp. 15–18, 22 | P1, P3, P7 | [`ids.py`](../src/ontology/ids.py) handles ingestion identity and rejects ambiguous name matches. Conversational candidate resolution and clarification remain to be built. |
| Govern tools, retries, and termination | VL05 pp. 13, 19–28 | P4, P5, P6, P7 | [`runtime/client.py`](../src/runtime/client.py) exposes engine commands; add the agent's allowed moves, guards, episode budget, stop reasons, and handoff. Engine resource limits are not an agent step budget. |
| Separate host execution from rule decisions | VL04 pp. 30–35; VL05 pp. 15–20 | P1, P4, P5 | Python hosts external calls; FrameX decides what follows from evidence. This repo has no model-call adapter or model-call receipts yet. |
| Preserve outcome and evidence in prose | VL05 pp. 29–35 | P3, P7 | [`output.py`](../src/cli/output.py) formats engine answers; add an agent result contract preserving true, false, unknown, empty, and error, plus scope and evidence. |
| Explain missing evidence | VL05 pp. 31–32 | P7, P8 | [`Session.explain`](../src/runtime/session.py) and the client support engine inspection; define task-specific evidence gaps and questions that could settle them. |
| Record and replay external calls | VL04 p. 40; VL05 pp. 13–20, 37 | Cross-cutting | Client transcripts and generated manifests exist. Add dated model/tool receipts with inputs, outputs, status, and the validated/executed request. A transcript alone is not the full agent record. |
| Govern persistent memory | VL05 pp. 36–45; decision sheet lane D | P11 (+ P1/P5) | No conversational memory layer exists here. Define source authority per slot, admission, supersession, current-value recall, and withdrawal behavior if the task needs persistence. |
| Evaluate the chosen architecture | VL05 p. 46; EvoSym report, Evaluation | All selected | Reuse [`tests/`](../tests/) and add checks for each new boundary; compare the same lookup, derived, ambiguous, and incomplete cases. |

## What H1 already established

EvoSym implemented source-data ingestion, stable identities, an ontology,
rule-derived answers, explicit open-world semantics, multi-hop queries,
explanations, independent expected answers, counterfactual checks, and timing.
Its report leaves the natural-language-to-query layer as future work.

This starter already supplies ingestion, declarative mappings, a rail ontology,
persistent sessions, staged loading, validation, explanations, and local
regression tests. Reuse these modules; use EvoSym as a reference for evaluation,
not as an alternative runtime to copy wholesale.

## Constraints to carry into H2

- Preserve open-world reasoning: no evidence does not mean false. The pattern
  repo's car world is closed, so adapt its outcome handling deliberately.
- Preserve scope: a connection derived from a dated service snapshot does not
  establish live availability or a future service guarantee. See [ontology](ontology.md).
- A valid request can still ask the wrong question. Test semantic grounding as
  well as schema validity; clarify ambiguous station names rather than guessing.
- Keep technical failure, rejected requests, unclear language, unknown evidence,
  and a valid empty result distinguishable throughout the interface.
- For each chosen composition, check the [five invariants](patterns.md#select-and-compose).
- Use small deterministic cases for development; daily SBB snapshots require
  their operating day and are covered separately by opt-in tests.

## Local baseline and commands

The Python client and locally built engine are pinned to commit
`48b5f077f542e0c44a18874871b82a899161128a` in `pyproject.toml`.
The engine belongs in this repo's `.venv/bin`, independently of `imp`.

```sh
uv run framex --version
uv run ruff check
uv run ty check
uv run pytest -q
```

To rebuild the engine after changing the pin, run `uv sync` followed by
`sh scripts/install-engine.sh`. No generated SBB workspace or LLM provider setup
is implied by installing the engine. Follow [usage](usage.md) for datasets and
[development](development.md) for opt-in snapshot tests.
