# Operations — UX-creator-agent

Release, dependency-update, and CI policy. Product documentation lives in
the README and `docs/`; design decisions live in `docs/adr/`.

## Verification stages

`scripts/verify_all.py` gates every change:

- `docs` — markdown-only changes: verify_docs + git diff --check
- `fast` — ruff check, ruff format --check, pyright (strict), pytest,
  verify_docs, git diff --check
- `standard` — fast + `check_plugin_load.py` (SDK 1.49.6 plugin load) +
  locked-image e2e on `examples/smart-kettle` (`e2e_authoring.py`) +
  `check_ruby_dsl.py` inside the image
- `ruby` — Ruby DSL parity/lint/minitest inside the image only

## Dependency updates

`scripts/check_dependency_updates.py` polls the external sources below;
run it locally whenever `pyproject.toml` or
`docker/ux-tools.Dockerfile` pins change. Deferrals (with reasons and a
re-check deadline) go in `scripts/dependency_update_deferrals.json`.

| Source | Where pinned |
|---|---|
| PyPI packages (pydantic, mcp, dev deps) | `pyproject.toml` + `uv.lock` |
| uv (`UV_VERSION`, image tag) | Dockerfile + `astral-sh/uv` releases |
| `ruby:*-slim-trixie` base digest | Dockerfile FROM |
| `SEMERU_JRE_VERSION` (+sha256) | Dockerfile ARG — `ibmruntimes/semeru27-binaries` releases |
| `PLANTUML_VERSION` (+sha256) | Dockerfile ARG — `plantuml/plantuml` releases (mit jar) |
| `MRUBY_VERSION` (+sha256) | Dockerfile ARG — `mruby/mruby` releases |
| `MERMAID_CLI_VERSION` | Dockerfile ARG — `mermaid-js/mermaid-cli` releases |
| `RUBOCOP_VERSION`, `MINITEST_VERSION` | Dockerfile ARG — rubygems |
| Node.js / Chromium / Graphviz | Debian trixie apt (rolling with the release) |
| openhands-sdk/-tools `1.49.6` | `pyproject.toml` sdk-check group |
| GitHub Action SHAs | `.github/workflows/*.yml` + `dependabot.yml` |

When bumping, review the complete changelog of each updated component
and record adoption decisions in the PR or `docs/research/` (see the
repo rules).

## Image publishing and the digest lock

`docker/image-digests.json` and the per-skill `tools-image.json` files
are written **only** by `publish-ux-images.yml` after a successful build,
smoke, and manifest record. Until the first publish, the lock is absent:

- `ux_launcher.py` and `run_in_locked_image.py` resolve the image from
  `$UX_TOOLS_IMAGE` or the digest lock; with neither resolvable they exit
  non-zero with an explicit "no image resolvable" error — never a silent
  local build.
- `locked-image-check.yml` and `verify_all.py --stage standard`/`ruby`
  require the lock or `UX_TOOLS_IMAGE` and are skipped/fail loudly
  otherwise.
- Doctor (`--warn` at session start) reports the missing lock as a
  warning and exits 0.

## Release flow

`release.yml` (manual dispatch, semver tag): verifies `plugin.json` /
`pyproject.toml` versions match the tag, runs the standard stage, builds
`dist/` artifacts (`ux-plugin-v*`, `ux-samples-v*`), and publishes the
GitHub release. CHANGELOG `[Unreleased]` is folded into the versioned
section by `scripts/bump_version.py`.

## CI hygiene

- `workflow-lint.yml` runs actionlint + zizmor on every workflow change.
- `locked-image-check.yml` fails PRs that drift the Dockerfile/lock.
- `digest-lock-sweep.yml` re-verifies the locked digest weekly.
- `check-dependency-updates.yml` opens issues for stale pins.
- `main-ci-failure-issue.yml` and `pr-branch-cleanup.yml` keep the board
  and branch list clean.
