# Dependency updates

This document records the pinned versions in use, where they come from, and
the adoption decision for each. Update it in the same change that touches
`pyproject.toml`, a workflow pin, or a new external source.

## Runtime dependencies (pyproject.toml + uv.lock)

| Package | Pin | Source | Decision |
| --- | --- | --- | --- |
| pydantic | `>=2` | PyPI | Floor pin — v2 API only (`model_validate`, `model_dump`). |
| mcp | `>=1.29,<2` | PyPI | stdio server boundary; `<2` caps the breaking major. |

## SDK check group (plugin-load / install smoke only)

| Package | Pin | Source | Decision |
| --- | --- | --- | --- |
| openhands-sdk | `==1.52.0` | PyPI | Exact pin — plugin API contract; same pin as the sibling plugins so a merged conversation sees one SDK. |
| openhands-tools | `==1.52.0` | PyPI | Exact pin — matches SDK. |

The `sdk-check` group is installed by default (`tool.uv default-groups`) so
pyright strict can type `check_plugin_load.py`; the Docker image excludes it
via `uv export --no-dev`.

## Dev dependencies (dev group)

| Package | Pin | Notes |
| --- | --- | --- |
| packaging | `>=26` | Used by `scripts/check_dependency_updates.py` |
| pyright | `>=1.1.414` | strict mode |
| pytest | `>=9` | suite runner |
| pytest-cov | `==7.1.0` | Coverage floor in the fast verification stage |
| pytest-xdist | `>=3` | `-n auto --dist loadgroup` |
| ruff | `>=0.16` | lint + format |

## Tooling pins

| Tool | Pin | Where |
| --- | --- | --- |
| uv | `==0.12.23` | `[tool.uv] required-version` |
| Python | `>=3.12`, CI matrix 3.12/3.13/3.14 (+3.15 canary) | pyproject `requires-python` |
| zizmor | `1.30.1` (uvx pin) | `workflow-lint.yml` |

## GitHub Actions pins

All `uses:` entries are pinned to a 40-char SHA with a `# vX.Y.Z` comment:

| Action | Pinned version |
| --- | --- |
| actions/checkout | v7.0.1 |
| astral-sh/setup-uv | v10.2.0 |
| actions/upload-artifact | v7.0.1 |
| actions/attest-build-provenance | v4.2.2 |
| actions/attest | v4.2.2 |
| actions/dependency-review-action | v5.0.0 |
| anchore/sbom-action | v0.24.3 |
| aquasecurity/setup-trivy | v0.3.1 |
| aquasecurity/trivy-action | v0.36.0 |
| docker/build-push-action | v7.4.0 |
| docker/login-action | v4.6.0 |
| docker/setup-buildx-action | v4.4.1 |
| github/codeql-action/upload-sarif | v4.38.2 |
| hadolint/hadolint-action | v3.5.0 |
| ossf/scorecard-action | v2.4.4 |
| step-security/harden-runner | v2.21.1 |

## Docker image pins

| Item | Pin | Where |
| --- | --- | --- |
| ruby base image | `ruby:4.0.7-slim-trixie` (digest-pinned) | `docker/ux-tools.Dockerfile` `FROM` |
| uv | `0.12.23` (+ `UV_DIGEST`) | `docker/ux-tools.Dockerfile` `ARG UV_VERSION` (must equal `[tool.uv] required-version`) |
| Python in image | `3.14` | `uv python install` inside the Dockerfile |
| IBM Semeru OpenJ9 JRE | `27.0.0.0` (+sha256) | `ARG SEMERU_JRE_VERSION` — `ibmruntimes/semeru27-binaries` releases |
| PlantUML MIT jar | `1.2026.8` (+sha256) | `ARG PLANTUML_VERSION` — `plantuml/plantuml` releases |
| mruby | `4.0.0` (+sha256) | `ARG MRUBY_VERSION` — `mruby/mruby` releases |
| mermaid-cli | `11.17.0` | `ARG MERMAID_CLI_VERSION` — `mermaid-js/mermaid-cli` releases |
| rubocop / minitest / json | `1.91.0` / `6.0.6` / `2.19.2` | Dockerfile ARGs — rubygems |
| Debian 13 (trixie) packages | unpinned | apt install layer (graphviz, chromium, nodejs, npm, CJK fonts, build tools, libpcre2-8-0) |

## Workflow git clone pins

| Item | Pin | Where |
| --- | --- | --- |
| CISOfy/lynis | `3.1.7` | `git clone --depth 1 --branch` in `container-audit.yml` |

The checker treats the `git clone --branch <ref>` pin in
`container-audit.yml` as the `workflow-pin` surface and compares the ref
against the upstream repo's highest semver tag, so a new Lynis release
surfaces in the weekly report.

## Checked by `scripts/check_dependency_updates.py`

The checker renders a per-surface markdown report (plus optional JSON) with
state columns `update available` / `deferred` / `up to date` / `unknown`.
Surfaces:

- `pypi` — runtime, sdk-check, and dev dependencies; `current` is the
  version resolved in `uv.lock`, compared against the latest PyPI release
  (spec floors do not count as current).
- `pypi-lock` — transitive `uv.lock` drift from `uv lock --upgrade
  --dry-run` (Update/Add/Remove lines); only drifted entries are listed.
- `uv-pin` — `[tool.uv] required-version` against PyPI `uv`.
- `python-version` — Python minors referenced by `requires-python`, the
  Dockerfile `uv python install`, and the CI matrix, against the latest
  stable CPython minor tag.
- `github-actions` — `uses:` SHA pins against the latest repo tag (the
  `# vX.Y.Z` comment is the recorded current version).
- `pypi-uvx` — `uvx tool@version` pins in workflows against PyPI.
- `docker-arg` — Dockerfile `ARG` pins (`UV_VERSION`,
  `MERMAID_CLI_VERSION`, `SEMERU_JRE_VERSION`, `PLANTUML_VERSION`,
  `MRUBY_VERSION`) against the mapped upstream repos.
- `docker-base` — the runtime `FROM` image tag; the `ruby:*-slim-trixie`
  base is reported as an unhandled image (presence only).
- `workflow-pin` — the `git clone --branch` lynis pin in
  `container-audit.yml` against `CISOfy/lynis` tags.

The weekly workflow posts the markdown report to the "Dependency update
check report" issue. Deferred candidates are recorded in
`scripts/dependency_update_deferrals.json` as
`{surface, name, latest, review_by, reason}`; `name` may be `"*"` to cover
a whole surface entry (e.g. every Python-version row). A deferral applies
only while `review_by` has not passed and still matches the reported
`latest`, so expired or superseded deferrals re-list automatically.

## Procedure

1. Run `uv run python scripts/check_dependency_updates.py` locally.
2. For each candidate, read the upstream release notes: record used APIs,
   defaults, breaking changes, and the adoption decision under
   `docs/research/` (see the SDK v*.*.* feature evaluations).
3. Bump the pin in the same change (pyproject/uv.lock via `uv lock`,
   workflow SHA + comment, or `uvx` pin) and refresh this file's tables.
4. Run `verify_all.py --stage fast`.
5. If deferring: add `{surface, name, latest, review_by, reason}` to
   `scripts/dependency_update_deferrals.json`.

## Current deferrals

| Surface | Name | Latest | Re-check | Reason |
| --- | --- | --- | --- | --- |
| pypi | mcp | 2.3.0 | 2027-04-01 | `openhands-sdk` 1.52.0 requires `fastmcp>=3.2.0,<4`, which caps `mcp<2`. |
| docker-arg | MERMAID_CLI_VERSION | 12.0.0 | 2027-04-01 | mermaid-cli 12.x requires Node >=22.13; the image runs Debian nodejs 20.19.x. |

## Not covered

- `docker/image-digests.json` and `plugins/ux/skills/*/tools-image.json`
  are digest locks written only by `publish-ux-images.yml` — never edited
  by hand.
- Transitive dependencies stay pinned in `uv.lock`; the `pypi-lock`
  surface reports drift but bumps still ride direct spec changes
  (`uv lock --upgrade` when applied).
- The `ruby:*-slim-trixie` base digest (rolling tag + sha256 pin; no
  upstream tag comparison exists for it).
- Debian/apt, gem, and npm packages inside the image beyond the tracked
  ARGs (apt tracks the Debian archive).

## Decisions — 2026-10-05 round (SDK 1.52.0)

| Component | From -> To | Decision |
| --- | --- | --- |
| `openhands-sdk` / `openhands-tools` (sdk-check group) | 1.51.0 -> 1.52.0 | Adopted. All 19 upstream commits reviewed; see [SDK v1.52.0 feature evaluation](research/sdk-v1.52.0-feature-evaluation.md). |
| mcp | stays <2 | Deferred: `openhands-sdk` 1.52.0 still requires `fastmcp<4` -> `mcp<2`; reason refreshed to cite 1.52.0, `review_by` unchanged. |

## Decisions — 2026-10-04 round (GitHub Actions latest-state wave)

| Component | Change | Decision | Reason |
| --- | --- | --- | --- |
| actions/cache | v5.0.5 -> v6.1.0 | adopted | v4's Node20 runtime was deleted 2026-09-23; v6.1.0 is the ESM line the family standardizes on. SHA `55cc8345…`. |
| uv | 0.12.22 -> 0.12.23 | adopted | Patch release; required-version, `UV_VERSION`, `UV_DIGEST`, and the setup-uv `version:` input move in lockstep. |
| CPython | matrix 3.12/3.13 -> +3.14, scalar pins -> 3.14, +3.15 canary | adopted | Latest stable minor; the 3.15 experimental leg reports via `::warning::` (step-level continue-on-error keeps the check green). |
| codeql-action | new shared `codeql.yml` (actions + python) | adopted | Needs repo-level default setup disabled before uploads succeed — tracked family-wide. |
| checker coverage | python-version scans all workflows + `.python-version` + Dockerfile `uv venv`/`python3.x`; RUBOCOP/MINITEST/JSON gem ARGs monitored via rubygems.org | adopted | Coverage audit found these pins unmonitored. |
