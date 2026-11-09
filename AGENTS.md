# Project guidance

## Read only what the task needs

- Start with `README.md` for the project overview and commands.
- For H2 preparation and lecture concepts, use `docs/course-lookup.md` to select the relevant VL04/VL05 pages and local modules before opening PDFs.
- For Hybrid AI pattern selection or implementation, use `docs/patterns.md` first, then read only the matching example and required shared files. Do not load the whole reference repository or notebook into context.
- Use `docs/ontology.md` for semantics, `docs/data.md` for datasets, `docs/usage.md` for commands, and `docs/development.md` for runtime architecture and tests.
- Search with `rg` and read targeted sections before expanding scope.

## Architecture decisions

- `docs/adrs/` is the source of truth for architecture decisions. Read relevant ADRs before changing the behavior they cover.
- Record new decisions in numbered files (`NNNN_short_title.md`) using `docs/adrs/0000_template_adr.md` as the structural reference. Replace its example title, date and content.
- Update the relevant ADR when an implementation changes an existing decision.
- **Hard limit: 3,000 characters per ADR**, including the entire file: headings, metadata, whitespace, links and amendments. Count characters, not words. Keep implementation details in other docs and link to them.
- State the context, decision, alternatives considered, and material consequences within that limit.

## Implementation and validation

- Use `uv` for Python commands and the dependencies declared in `pyproject.toml`.
- Keep changes focused and functions responsible for one coherent task. Follow existing package boundaries under `src/`.
- Keep `uv run ruff check` and `uv run ty check` clean on code you touch. Report unrelated existing failures separately.
- Run relevant tests with `uv run pytest`; the full local suite is `uv run pytest -q`. Engine integration tests require the FrameX binary; full-snapshot tests are opt-in. See `docs/development.md`.
- FrameX owns reasoning; Python maps data, orchestrates sessions and presents results. Preserve open-world semantics: missing evidence remains unknown.
- Keep the Python FrameX client and Rust engine pinned to the same commit in `pyproject.toml`. The existing `scripts/install-engine.sh` builds the engine into `.venv/bin`; changing the client dependency alone does not update the engine.
- Treat the sibling pattern repository as reference material. Adapt examples to this project's runtime and ontology rather than copying its transport or car-world assumptions.
