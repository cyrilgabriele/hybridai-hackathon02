# 1. One small FrameX world per refund decision

Date: 2026-11-10

## Status

Accepted

## Context

The refund chat must answer while the passenger waits. The rules in `46-refunds.fx` read each `RefundCase` and `DelayCheck` under `NOT` and aggregates. `add` recomputes the whole knowledge base, and the incremental path falls back to that for such rules. On one session of the full `fx/` workspace this took 27 s for the first case and 166 s by the third.

## Decision

Each decision loads a fresh engine holding the unchanged rule files of `fx/` (those before `60-`), FrameX's `competence.fx`, our gate, and only the trips those rules can use: trips at the origin in the case window, and trips at the destination that a change from one of them could reach within the rules' own bounds. See [knowledge.py](../../src/pipeline/knowledge.py), the only code that writes FrameX source for a case, always from checked identifiers.

Planned connections must arrive after they depart (`46-refunds.fx`). Two services reported under one trip reference otherwise form a phantom train that hides every real departure.

## Alternatives considered

- One long-lived session with `add`: simplest, but too slow and its cost grows with each case.
- Reducing the rules or computing delays in Python: faster, but moves reasoning out of FrameX.

## Consequences

Offers take about 5 s and verdicts about 13 s, and the cost does not grow. Results matched the full workspace on the routes compared. Selecting trips duplicates knowledge of the rules' search, so a change to that search must update `select_trips`. Each world uses about 2 GB, so decisions run one at a time. Proofs of aggregates can exceed 50 MB; the view shows the first lines.
