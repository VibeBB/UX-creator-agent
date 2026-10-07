# AGENTS.md — VibeBB UX-creator-agent

Guidance for AI agents and humans working on this repository. It is the
**VibeBB UX design sibling** in a family of 11 OpenHands plugin
repositories. UX-creator coordinates the ten sister plugins below through
workspace contracts and liaison records.
UX-creator orchestrates UX *contracts* — personas, JTBD jobs, journeys,
service blueprints, statecharts, QCD — and projects them into diagrams
(Mermaid, PlantUML, XState, SCXML, Storybook).

| Sister repository | Target | Primary contribution |
| --- | --- | --- |
| `bard-agent` | `bard` | Sound cues and music |
| `electrical-circuit-agent` | `circuit` | Electrical design |
| `dashboard-agent` | `dashboard` | Operator and telemetry UI |
| `document-agent` | `doc` | User and maintainer documentation |
| `firmware-agent` | `firmware` | Embedded software |
| `fpga-agent` | `fpga` | Programmable logic |
| `mechanical-agent` | `mech` | Enclosure and mechanical design |
| `production-engineering-agent` | `prodeng` | Manufacturing and production engineering |
| `simulation-agent` | `sim` | Simulation and analysis |
| `wire-agent` | `wire` | Electrical wiring and harnesses |

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
- UX output files are `{product}.ux.json`, `*.ux-proposals.json` +
  `*.triage.json`, hash-bound SLP v2 `*.ux-request.json` and
  `*.ux-response.json` liaison files, `out/<name>/` projections
  (`*.journey.mmd`, `*.statechart.{mmd,puml,xstate.json,scxml}`,
  `*.wireframe.puml`, `*.blueprint.puml`, `*.emotion.mmd`/`*.emotion.json`, `*.mindmap.mmd`,
  `*.sequence.puml`, `*.wbs.puml`,
  `*.stories.json`, `*.odi.csv`, `manifest.json`,
  `provenance.json`, `ux-report.json/.md`), `*.ux-request.json`, and
  `*.ux-vision.jsonl` advisory records.
- VRP decisions, impressions, and vision reviews are JSONL records under
  `observations/<plugin>/` (`decisions.jsonl`, `impressions.jsonl`,
  `vision-reviews.jsonl`). Sister request and
  response files are strict v2 records with workspace-relative SHA-256
  input/artifact references, timezone-aware timestamps, and explicit
  responder and gate evidence.
- **Do not mutate an authored contract** — it is re-derived from the
  Ruby DSL or the `author`/`import` entry points; the gates gate, not
  post-edits.
- Keep everything deterministic and auditable: projections, sha256
  provenance, `unknown` over silent skips.
- All UX knowledge (JTBD, ODI, CJM, HIG, game design, persona, Ruby
  style) lives in `plugins/ux/skills/*/SKILL.md`; agent prompts
  summarize and link to skills. Skills use `triggers:` (keyword); a
  `paths:` glob list makes a skill a path-triggered rule instead
  (`ux-contract-rules`, `ux-out-rules`) — the two mechanisms are
  exclusive, so rules live in their own `skills/` entries.
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
                        requests, proposals, responses, production,
                        advisory, report,
                        render, doctor, ruby_bridge, cli, mcp_server
plugins/ux/             OpenHands plugin (agents, commands, skills, hooks,
                        launcher, .mcp.json)
ruby/                   ux-dsl library, runner, rubocop config, minitest
docker/                 ux-tools Dockerfile, puppeteer-config.json
examples/               smart-kettle (.ux.rb + generated .ux.json),
                        smart-kettle-product (CMF, content, bard cues,
                        production plan)
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

`verify_all.py` also accepts `--group` (lint/unit/docker), `--match`, and
`--shard K/N` to run a subset of a stage's commands so CI can spread one
stage across jobs; `--list` dumps the tagged command table.

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
- `ensure_llm_profiles.py`, `ensure_agent_profiles.py`, and
  `safety_rail.py` are canonical across the family; `_provenance.py` is
  optional and absent in UX and Production Engineering. Change canonical
  copies together and update `EXPECTED` in
  `scripts/check_shared_hooks.py`.
- `intake_attachments.py`, `protect_generated.py`, `report_ux_status.py`,
  `record_*`, and `ux_doctor.py` hooks are intentionally repo-specific.
- High-risk SLP v2 sibling requests must cite a declared job id —
  enforced in `requests.py` and the `ux-liaison` agent/skill. Reconcile
  request lifecycle states through `python -m ux_creator liaison`; the
  states are `open`, `answered`, `mismatched`, `stale`, `broken`,
  `blocked`, and `circular`. Production gates consume request completion,
  request ownership, liaison integrity, and sister-record evidence.
- Vision observations are typed L2 advisory records only — never
  verdicts, never gate inputs.

Shared workflows are canonical across the family; change all 11 copies together and update `EXPECTED` in `scripts/check_shared_workflows.py`.

## CI/CD

Digest-lock PRs use `scripts/publish_image_pin_pr.sh`: the publisher
dispatches `ci.yml` and `workflow-lint.yml` on the lock branch, then polls
the authoritative required-check set for up to 15 minutes. Non-required
failures do not block publishing; a concluded required-check failure or a PR
closed without merge fails the job. A PR merged externally triggers the
existing post-merge main workflows. If required checks are still pending at
the deadline, the publisher arms squash auto-merge with branch deletion and
exits successfully.

The release bump-version state machine lives in `scripts/release_bump.sh`
(the workflow step is a thin wrapper) and is covered by
`tests/test_release_bump.py`, which exercises it against a stubbed `gh` and
local git remotes. `release.yml`'s `dry_run` input rehearses the release:
version arithmetic and tag checks run and downstream jobs still execute,
but nothing is committed, pushed, tagged, or released.

`publish-ux-images.yml` accepts a `dry_run` dispatch input that rehearses
the publish: the image builds into the local daemon (`push: false`,
`load: true`) and the Trivy gate, SBOM chain, measurements, and smoke
checks still run against the local tag, but nothing is pushed, `:latest`
is not promoted, no attestation is stored, the digest-lock PR is not
opened, and no SARIF reaches code scanning.

SPDX SBOM generation prefers registry pulls (the local daemon under
`dry_run`), uses runner temporary storage, and disables file metadata. The
attested SBOM is package-level SPDX 2.3; file entries and relationships
involving files are omitted to stay below 16 MiB. The full Syft SBOM is
attached to the workflow run as a 90-day artifact.
