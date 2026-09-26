# Contributing

Thank you for your interest in UX-creator-agent.

## Getting started

```bash
uv sync
uv run python scripts/verify_all.py --stage fast
```

Read `AGENTS.md` first — it defines the invariants (fail-closed gates,
projection purity, plugin boundary, dependency-update policy).

## Pull requests

- English title; body follows `.github/PULL_REQUEST_TEMPLATE.md`
  (`Summary` + `Test plan`).
- One logical change per commit, `feat(scope): ...`-style messages.
- Run `verify_all.py --stage fast` before pushing; `--stage standard`
  for contract/gate changes (requires the locked image).
- Adding a dependency or an external source requires updating
  `scripts/check_dependency_updates.py`, `docs/operations.md`, and — for
  deferrals — `scripts/dependency_update_deferrals.json`, plus an ADR
  under `docs/adr/` when the choice is load-bearing.

## License

By contributing you agree your work is licensed under the BSD 3-Clause
License (see `LICENSE`).
