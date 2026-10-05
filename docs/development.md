# Development

This guide is for maintainers working in a repository checkout. The product
workflow for AgentCanvas/OpenHands users is in the root
[README](../README.md).

## Environment

- Python 3.12 or newer and `uv` are required for the host development
  workflow.
- Docker and access to the locked `ux-tools` image are required for standard
  verification and the Ruby/render toolchain.
- `pyproject.toml` and `uv.lock` are the dependency source of truth. Use
  `uv sync --locked` before running checks.
- Do not run mmdc, PlantUML, or mrbc directly on the host for CI-like
  verification; use `scripts/run_in_locked_image.py`.

## Change locations

- Core schemas and behavior: `src/ux_creator/`.
- OpenHands agents, commands, skills, hooks, and launcher:
  `plugins/ux/`.
- Authored demonstration contracts and SLP records: `examples/`.
- Tests: `tests/`.
- Design decisions and maintainer/product documentation: `docs/`.
- Image and repository checks: `scripts/`.

Keep prompts in English with source comments and docs. The root README is the
only file in this documentation set that includes Japanese. Update the docs
index and relevant coverage tests whenever a user-facing asset changes.

## Verification

The canonical staged verification is `scripts/verify_all.py`; a docs-only
edit can start with the docs stage. Before handing off code changes, run the
prescribed checks:

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pyright
env -u BASH_ENV -u "BASH_FUNC_gh%%" uv run pytest -n auto
uv run python scripts/verify_docs.py
uv run python scripts/check_shared_hooks.py
uv run python scripts/check_shared_workflows.py
uv run --group sdk-check python scripts/check_plugin_load.py
uv run python scripts/verify_all.py --stage fast
sha256sum plugins/ux/hooks/scripts/_records.py plugins/ux/hooks/scripts/require_records.py
uv run python scripts/verify_all.py --stage standard
```

The standard stage uses the digest-pinned image for the authoring e2e. Report
an exact Docker/image resolution error if that stage is unavailable; do not
replace it with an unpinned local run and call it equivalent.

Useful scoped commands during development:

```bash
uv run python scripts/verify_all.py --stage docs
uv run pytest tests/test_docs_coverage.py
uv run pytest tests/test_liaison_e2e.py tests/test_example_liaison.py
uv run pytest tests/test_mcp_server.py
```

When changing the shared hook or workflow copies, keep the family copies
identical and update no hash allowlist to bypass the shared-file checker.
When adding dependencies, use an ADR and update the dependency policy.

## Working tree and commits

Make one focused local commit per implementation step with an English
`feat(scope): ...` or documentation commit message. Stage paths explicitly.
Do not commit generated `out/` artifacts, secrets, or environment files.
Leave pushing and PR lifecycle to the repository owner.
