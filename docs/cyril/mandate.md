# Cyril — Auditor

## Mandate for Hackathon 02

- **Constraints:** verify that the model never writes or runs unchecked rules or queries.
- **Acceptance on evidence:** verify that acceptance depends on supporting evidence rather than model confidence or plausibility.
- **Invariant protection:** identify which invariants the design endangers and explain how each is protected.

## Audit focus

For each model-to-system boundary, record what is proposed, which checks run
before it takes effect, what evidence permits acceptance, and what happens
when a check fails or evidence is missing. Check that these protections are
enforced by the implementation and demonstrated by tests.

Use the [pattern guide's five invariants](../patterns.md#select-and-compose)
and the [VL04/VL05 course lookup](../course-lookup.md) as references. For each
endangered invariant, document the failure case, the protection, and the test
or execution evidence that demonstrates it.
