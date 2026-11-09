# Hybrid AI pattern lookup

Reference implementations live in the sibling repository
[`hybrid-ai-patterns-examples`](../../hybrid-ai-patterns-examples/), locally at
`/Users/cyrilgabriele/Documents/School/00_Courses/02_HNS_AI/hybrid-ai-patterns-examples`.
These are teaching examples to adapt, not implementations already present in this project.

Choose a row by the responsibility you need. Read its single Python file first;
follow the shared-file table only when needed. Avoid reading the full notebook,
all ten examples, or the transport implementation for a pattern-level task.

| # | Pattern / when to use | Implementation | Key behavior |
|---|---|---|---|
| 01 | Model as Sensor: extract facts from text | [Python](../../hybrid-ai-patterns-examples/src/01_model_as_sensor/pattern_model_as_sensor.py) | Model proposes values with quotes; host checks quote occurrence; rules accept readings. |
| 02 | Model as Author: draft a rule from policy | [Python](../../hybrid-ai-patterns-examples/src/02_model_as_author/pattern_model_as_author.py) | Test the draft in a fresh world against predefined cases; a person adopts it. |
| 03 | Model as Translator: natural-language query and answer | [Python](../../hybrid-ai-patterns-examples/src/03_model_as_translator/pattern_model_as_translator.py) | Translate question to query, obtain verdict and proof, then phrase the result. |
| 04 | Model Proposes, Rules Dispose: admit or reject actions | [Python](../../hybrid-ai-patterns-examples/src/04_model_proposes_rules_dispose/pattern_model_proposes_rules_dispose.py) | Execute only admitted proposals; feed refusal conditions back; at most three attempts. |
| 05 | Rules Steer the Model: rules control a workflow | [Python](../../hybrid-ai-patterns-examples/src/05_rules_steer_the_model/pattern_rules_steer_the_model.py) | Rules select the next check; model phrases questions and interprets answers. |
| 06 | Critique and Repair: correct generated code using checks | [Python](../../hybrid-ai-patterns-examples/src/06_critique_and_repair/pattern_critique_and_repair.py) | Check syntax and required facts; return specific feedback; stop on repetition or three attempts. |
| 07 | Division by Competence: defer unresolved cases | [Python](../../hybrid-ai-patterns-examples/src/07_division_by_competence/pattern_division_by_competence.py) | Check positive and negative rule conclusions first; model assesses unresolved cases for a person. |
| 08 | Model as Hypothesis Generator: test possible explanations | [Python](../../hybrid-ai-patterns-examples/src/08_model_as_hypothesis_generator/pattern_model_as_hypothesis_generator.py) | Test each assumption in a fresh world for explanatory power and contradictions; hypotheses stay provisional. |
| 09 | Model as Critic of the Rules: review rules against policy | [Python](../../hybrid-ai-patterns-examples/src/09_model_as_critic_of_the_rules/pattern_model_as_critic_of_the_rules.py) | Model flags policy gaps with quotes; grounded remarks become review findings; no automatic rule edits. |
| 10 | Rules Teach the Model: provide rule-labelled examples | [Python](../../hybrid-ai-patterns-examples/src/10_rules_teach_the_model/pattern_rules_teach_the_model.py) | Put rule labels and reasons in the prompt; grade new model answers against the rules. |
| 11 | Rule-Governed Memory: persist and revise facts across sessions | No Python example in the sibling repo; see [VL05](../../01_lectures/VL05_Agentic_AI.pdf), pp. 36–45, and the [course lookup](course-lookup.md). | Rules admit writes by source and slot; newer accepted values supersede older ones; recall uses current valid facts. |

## Select and compose

Use the one-page [pattern decision sheet](../../02_exercises/03_week/HybridAIPatternDecision.pdf)
to choose the responsibility needed first, then add patterns only for uncovered
requirements. It covers P1–P11; the sibling Python examples cover P1–P10.
P11 includes withdrawal of dependent facts when evidence is forgotten, beyond
the supersession example in VL05. Pair it with P1 for proposed writes and P5
when rules should control recall.

Check the sheet's five invariants for the whole composition:

1. Model output is data, never unchecked code.
2. Each answer is dated and replayable.
3. Rules decide what counts and happens.
4. Evidence, not confidence, governs acceptance.
5. Failure, invalid, unclear, and unknown stay distinct.

For each selected pattern, name who steers, what crosses the boundary, who has
the last word, and how long state lasts (VL04, p. 23). P3's teaching example
generates raw queries; VL05, pp. 24–25, instead uses a small operation vocabulary
with IDs and an adapter that constructs executable queries after validation.
Use that checked-request design when building an agent here.

## Shared references: open on demand

| Need | File / relevant entry |
|---|---|
| Rule definitions and facts used by an example | [`src/car_world.fx`](../../hybrid-ai-patterns-examples/src/car_world.fx): search for the class or slot queried by that example. |
| Session creation or refusal feedback | [`src/world.py`](../../hybrid-ai-patterns-examples/src/world.py): `car_world`, `reason_why_not`. |
| Model invocation and JSON parsing | [`src/llm.py`](../../hybrid-ai-patterns-examples/src/llm.py): `ask`, `ask_json`. Importing this module configures an OpenRouter client. |
| Example selection | [`src/main.py`](../../hybrid-ai-patterns-examples/src/main.py): menu or numbered pattern selection. Running examples can call an external model; pattern 05 also requests interactive input. |
| Reference client API | [`src/framex/README.md`](../../hybrid-ai-patterns-examples/src/framex/README.md); inspect [`framex.py`](../../hybrid-ai-patterns-examples/src/framex/framex.py) only for transport details. |

## Adapting a pattern here

Use this project's `src/runtime/session.py` for loaded knowledge-base sessions,
`src/runtime/client.py` for client extensions, and `src/runtime/query.py` for
engine discovery. See [development](development.md) and [ontology](ontology.md)
for architecture and semantics; use `src/ontology/emit.py` to emit facts.

The reference world declares `world closed.`; this project's rail ontology uses
an open world. Preserve `unknown` as distinct from `false`, especially when
adapting patterns 03, 07 and 10. The reference import `framex.framex` belongs to
its local client layout; this repo uses the pinned upstream `framex` package
with its own runtime adapter. The reference LLM helper and its dependencies are
not installed here merely by linking these examples.
