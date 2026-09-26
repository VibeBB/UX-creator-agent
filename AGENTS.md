# AGENTS.md — VibeBB UX-creator-agent

Guidance for AI agents and humans working on this repository. It is the
**VibeBB UX design sibling** in a family of OpenHands plugins
(`bard-agent`, `wire-agent`, `mechanical-agent`, `electrical-circuit-agent`)
that share the same contracts, hooks, and release pipelines.
UX-creator orchestrates UX *contracts* — personas, JTBD jobs, journeys,
service blueprints, statecharts, QCD — and projects them into diagrams
(Mermaid, PlantUML, XState, SCXML, Storybook).

## Authoring rules

- All executable logic is Python 3.12 under `src/ux_creator/` (stdlib +
  pydantic v2 + mcp). Ruby (`ruby/`) is a *design-expression runtime*
  only — the DSL builds contract JSON; judgement lives in `gates.py`.
- The agent reads and writes files under the OpenHands project
  directory; the shared workspace is the single source of truth.
- **`plugins/ux/`** — the plugin itself: `.plugin/plugin.json`,
  `agents/`, `commands/`, `skills/`, `hooks/`, `scripts/`, `.mcp.json`.
  Agent/command/skill files are Markdown with YAML frontmatter — do not
  put logic in them; every executable step delegates to
  `python -m ux_creator` inside the `ux-tools` container image.
- UX output files are `{product}.ux.json`, `out/<name>/` projections
  (`*.journey.mmd`, `*.statechart.{mmd,puml,xstate.json,scxml}`,
  `*.wireframe.puml`, `*.stories.json`, `*.odi.csv`, `manifest.json`,
  `provenance.json`, `ux-report.json/.md`), `*.ux-request.json`, and
  `*.ux-vision.jsonl` advisory records.
- **Do not mutate an authored contract** — it is re-derived from the
  Ruby DSL or the `author`/`import` entry points; the gates gate, not
  post-edits.
- Keep everything deterministic and auditable: projections, sha256
  provenance, `unknown` over silent skips.
- All UX knowledge (JTBD, ODI, CJM, HIG, game design, persona, Ruby
  style) lives in `plugins/ux/skills/*/SKILL.md`; agent prompts
  summarize and link to skills.
- See `docs/` for operations and ADRs.

## Voice and commit policy

- Code, comments, docs, and commit messages are English. Agent replies
  are fluent and technical; slang/jokes only in the designer persona
  (ux-persona skill).
- Commit style: `feat(scope): one-line imperative summary`, max 72 chars.
  One logical change per commit.
- PRs: English title, `Summary` + `Test plan` sections
  (`.github/PULL_REQUEST_TEMPLATE.md`).
- Do not add new dependencies without an ADR under `docs/adr/`.

## Docker image policy

- All UX tool execution runs inside `ghcr.io/vibebb/ux-tools` (the locked
  image) via `plugins/ux/scripts/ux_launcher.py` or
  `scripts/run_in_locked_image.py`. The host only needs uv + Python 3.12
  + git.
- Image contents are pinned in `docker/ux-tools.Dockerfile` and locked by
  `docker/image-digests.json` + `plugins/ux/skills/*/tools-image.json`
  (written by the publish workflow).
- Never run mmdc/plantuml/mrbc on the host inside CI — run them in the
  image.

## Repository layout

```
src/ux_creator/         Python core: contract, gates, projections, imports,
                        requests, advisory, report, render, doctor,
                        ruby_bridge, cli, mcp_server
plugins/ux/             OpenHands plugin (agents, commands, skills, hooks,
                        launcher, .mcp.json)
ruby/                   ux-dsl library, runner, rubocop config, minitest
docker/                 ux-tools Dockerfile, puppeteer-config.json
examples/               smart-kettle (.ux.rb + generated .ux.json)
scripts/                verify_all, check_plugin_load, run_in_locked_image,
                        e2e_authoring, check_ruby_dsl, publish/release helpers
tests/                  pytest suite (contract, gates, projections, imports,
                        requests, cli, hooks, plugin assets)
docs/                   operations, ADRs, research
.github/workflows/      ci, publish-ux-images, locked-image-check, release,
                        workflow-lint, digest-lock-sweep,
                        check-dependency-updates, pr-branch-cleanup,
                        main-ci-failure-issue
```

## Building, testing, and linting

```bash
uv sync                                              # creates/locks the venv
uv run python scripts/verify_all.py --stage fast     # ruff, pyright, pytest, docs
uv run python scripts/verify_all.py --stage standard # + locked-image e2e + plugin load
uv run --group sdk-check python scripts/check_plugin_load.py
```

- Lint: `uv run ruff check` (E,F,I,UP,B,SIM,RET,RUF,PTH,C4,DTZ,ASYNC,
  ISC,ICN,COM818,PLR0911,PLR0912,PLR0915), line length 100.
- Types: `uv run pyright` on `src` + `scripts` — strict mode.
- Tests: `uv run pytest -v -n auto` — never swallow exceptions, never
  soften assertions; every error reports `unknown`, not success.
- Ruby: `ruby -w -c`, rubocop, minitest — always inside the ux-tools
  image (`scripts/check_ruby_dsl.py`).

## Coding conventions

- Pydantic v2 `ConfigDict(frozen=True, extra="forbid")` for all models;
  `strict=True` on bounded numeric fields; fail-closed validators.
- Gates produce `GateReport`/`GateCheck` dataclasses (mirror of wire's):
  verdict ∈ {pass, fail, unknown}; `fail` blocks, `unknown` warns.
- Subprocess tools (`ruby`, `mrbc`, `mmdc`, `java -jar`) run through the
  bridge/render modules with explicit timeouts; missing binary →
  `unknown`.
- Stdlib-only outside pydantic/mcp; no `typing.Any` shortcuts, no
  network imports, `pathlib.Path` everywhere.

## Security and quality gates

- `protect_generated` and `safety_rail` pre-tool hooks deny edits to
  generated projections and dangerous shell writes inside the workspace
  (exit 2 + stderr reason).
- High-risk sibling requests (`ux-request.json`) must cite a job id —
  enforced in `requests.py` and the `ux-liaison` skill.
- Vision observations are typed L2 advisory records only — never
  verdicts, never gate inputs.
