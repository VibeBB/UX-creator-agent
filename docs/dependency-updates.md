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
| openhands-sdk | `==1.53.0` | PyPI | Exact pin — plugin API contract; same pin as the sibling plugins so a merged conversation sees one SDK. |
| openhands-tools | `==1.53.0` | PyPI | Exact pin — matches SDK. |

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
| actions/upload-artifact | v7.0.2 |
| actions/download-artifact | v8.0.2 |
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
| step-security/harden-runner | v2.22.1 |

## Docker image pins

| Item | Pin | Where |
| --- | --- | --- |
| ruby base image | `ruby:4.0.7-slim-trixie` (digest-pinned) | `docker/ux-tools.Dockerfile` `FROM` |
| uv | `0.12.23` (+ `UV_DIGEST`) | `docker/ux-tools.Dockerfile` `ARG UV_VERSION` (must equal `[tool.uv] required-version`) |
| Python in image | `3.14` | `uv python install` inside the Dockerfile |
| IBM Semeru OpenJ9 JRE | `27.0.0.0` (+sha256) | `ARG SEMERU_JRE_VERSION` — `ibmruntimes/semeru27-binaries` releases |
| PlantUML MIT jar | `1.2026.8` (+sha256) | `ARG PLANTUML_VERSION` — `plantuml/plantuml` releases |
| mruby | `4.0.0` (+sha256) | `ARG MRUBY_VERSION` — `mruby/mruby` releases |
| Node.js | `26.11.1` (+sha256) | `ARG NODE_VERSION` — `nodejs/node` releases; official tarball → `/usr/local` |
| npm vendored patches | brace-expansion `5.0.12`, undici `6.28.1` (+sha256) | Dockerfile ARGs — registry tarballs applied over `npm/node_modules`; pins follow npm's bundled majors, so they are intentionally NOT tracked as docker-arg surfaces |
| mermaid-cli | `12.0.0` | `ARG MERMAID_CLI_VERSION` — `mermaid-js/mermaid-cli` releases |
| rubocop / minitest / json | `1.91.0` / `6.0.6` / `3.0.2` | Dockerfile ARGs — rubygems |
| Debian 13 (trixie) packages | unpinned | apt install layer (graphviz, chromium, CJK fonts, build tools, libpcre2-8-0, openssl trio for deb13u3) |

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
  `MRUBY_VERSION`, `NODE_VERSION`) against the mapped upstream repos.
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
| pypi | mcp | 2.3.0 | 2027-04-01 | `openhands-sdk` 1.53.0 requires `fastmcp>=3.2.0,<4`, which caps `mcp<2`. |
| python-version | Python version (pyproject.toml) | 3.14 | 2027-01-08 | 3.12/3.13 remain the supported floor; 3.14+ is exercised by the canary legs. |
| python-version | Python version (ci.yml) | 3.14 | 2027-01-08 | 3.12/3.13 remain the supported floor; 3.14+ is exercised by the canary legs. |

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

## Decisions — 2026-10-08 round (GitHub Actions + Python floor deferral)

| Component | From -> To | Decision |
| --- | --- | --- |
| step-security/harden-runner | v2.21.1 -> v2.22.1 | Adopted across all workflows. v2.22.0 adds Linux ARM64 (community tier), GHES self-hosted VM support and macOS/Windows deny lists (enterprise tier); v2.22.1 fixes security-rule init and GHES connectivity on self-hosted runners. We run audit mode on GitHub-hosted Linux — none of the changes touch our usage. |
| actions/upload-artifact | v7.0.1 -> v7.0.2 | Adopted. Patch: improves artifact download retries on HTTP 429 (honors Retry-After); `@actions/artifact` 6.3.1. |
| actions/download-artifact | v8.0.1 -> v8.0.2 | Adopted. Same 429 retry improvement via `@actions/artifact` 6.3.1, plus readme updates. |
| Python floor | 3.12/3.13 -> 3.14 | Deferred to 2027-01-08. `requires-python` and the required CI legs stay on the supported floor; 3.14 runs as a required leg and 3.15 as the canary. |

## Decisions — 2026-10-08 round (Node 26.11.1)

| Component | From -> To | Decision |
| --- | --- | --- |
| Node.js | `26.11.0` -> `26.11.1` official tarball (+sha256) | Adopted. The 26.11.1 release (Current line, 2026-10-07) contains only three reverts of documentation build tooling (`build: toggle doc-kit verbosity based on V`, `build, doc: move to redesign`, `tools: bump the doc group in /tools/doc`) — no runtime, API, or security changes. |
| npm | bundled 11.20.0 (unchanged) -> still patched in place | Re-evaluated on this NODE_VERSION bump as recorded below. Latest npm is still 12.2.0, vendoring the same brace-expansion 5.0.9 + undici 6.28.0 the publish gate flags (verified 2026-10-08 via registry tarballs); Node 26.11.1's bundled npm 11.20.0 ships the same. The in-place patches (5.0.12, 6.28.1) stay. |

## Decisions — 2026-10-07 round (Node 26 migration)

| Component | From -> To | Decision |
| --- | --- | --- |
| Node.js | Debian `nodejs`/`npm` 20.19.x -> `26.11.0` official tarball (+sha256) -> `/usr/local` | Adopted. Debian trixie freezes nodejs at 20.x for its lifecycle; NodeSource was rejected (unverified pipe-to-bash, floating version, third-party apt repo). The tarball matches the image's verified-download convention and adds dep-checker tracking (`nodejs/node` tags). Node 26 reaches LTS on 2026-10-28 (EOL 2029-04); dashboard-agent already runs Node 26. |
| mermaid-cli | 11.17.0 -> 12.0.0 | Adopted. The Node >=22.13 blocker is resolved; the 2027-04-01 deferral is lifted early. |
| json gem | 2.19.2 -> 3.0.2 | Adopted. Changelog reviewed: 3.0 removes `create_additions` and rarely used aliases, defaults `allow_duplicate_key`/`allow_comments` to false — the DSL uses only `JSON.parse`/`JSON.generate`, no affected APIs. |
| npm | bundled 11.20.0 -> 12.2.0 | Not adopted. npm 12.2.0 still vendors brace-expansion 5.0.9 + undici 6.28.0 (the publish-gate findings) — no fix, extra churn; vendored deps patched in place instead. Re-evaluate on the next NODE_VERSION bump. |
| brace-expansion (npm vendored) | 5.0.9 -> 5.0.12 | Adopted in place — fixes CVE-2026-102276 + CVE-2026-102278 flagged by the publish Trivy gate. Patch release, same API. |
| undici (npm vendored) | 6.28.0 -> 6.28.1 | Adopted in place — fixes CVE-2026-19534. Patch within npm's vendored 6.x major; 7.x/8.x not adoptable until npm vendors them. |
| openssl Debian packages | 3.5.7-1~deb13u2 -> ~deb13u3 | Adopted via the apt install list (same pattern as libpcre2-8-0) — fixes CVE-2026-75804 + CVE-2026-84782 across libssl3t64, openssl, openssl-provider-legacy. |

## Decisions — 2026-10-07 round (SDK 1.53.0)

| Component | From -> To | Decision |
| --- | --- | --- |
| `openhands-sdk` / `openhands-tools` (sdk-check group) | 1.52.0 -> 1.53.0 | Adopted. All 6 upstream PRs reviewed; see [SDK v1.53.0 feature evaluation](research/sdk-v1.53.0-feature-evaluation.md). |
| mcp | stays <2 | Deferred: `openhands-sdk` 1.53.0 still requires `fastmcp<4` -> `mcp<2`; reason refreshed to cite 1.53.0, `review_by` unchanged. |

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
