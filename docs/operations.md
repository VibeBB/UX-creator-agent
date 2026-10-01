# Operations — UX-creator-agent

Release, dependency-update, and CI policy. Product documentation lives in
the README and `docs/`; design decisions live in `docs/adr/`.

## SBOM attestations

`publish-ux-images.yml` generates and attests an SPDX-2.3 SBOM for the
published tools digest and uploads it for 30 days. The returned URL is stored
as `sbom_attestation` and verified by `locked-image-check.yml` when present;
an absent URL warns and continues.

## Verification stages

`scripts/verify_all.py` gates every change:

- `docs` — markdown-only changes: verify_docs + git diff --check
- `fast` — ruff check, ruff format --check, pyright (strict), pytest,
  verify_docs, git diff --check
- `standard` — fast + `check_plugin_load.py` (SDK 1.50.1 plugin load) +
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
| openhands-sdk/-tools `1.50.1` | `pyproject.toml` sdk-check group |
| GitHub Action SHAs | `.github/workflows/*.yml` + `dependabot.yml` |

When bumping, review the complete changelog of each updated component
and record adoption decisions in the PR or `docs/research/` (see the
repo rules).

## Image publishing and the digest lock

`docker/image-digests.json` and the per-skill `tools-image.json` files
are written **only** by `publish-ux-images.yml` after a successful build,
provenance attestation, smoke, and tools record. Existing pins created
before provenance support remain usable without attestation metadata until
the next successful publish:

- `ux_launcher.py` and `run_in_locked_image.py` resolve the image from
  `$UX_TOOLS_IMAGE` or the digest lock; with neither resolvable they exit
  non-zero with an explicit "no image resolvable" error — never a silent
  local build.
- `locked-image-check.yml` and `verify_all.py --stage standard`/`ruby`
  require the lock or `UX_TOOLS_IMAGE` and are skipped/fail loudly
  otherwise.
- Published locks include the provenance attestation URL. The locked-image
  check verifies it against the publisher workflow; existing pins without
  provenance remain usable with a warning until the next successful publish.
- Publish and locked-image smoke outputs are uploaded even when the smoke
  fails, so the gate report remains available for diagnosis.
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
- `locked-image-check.yml` fails PRs that drift the Dockerfile/lock and
  prewarms the pinned image through `ux_launcher.py` before running the
  shipped authoring example.
- `digest-lock-sweep.yml` re-verifies the locked digest weekly.
- `check-dependency-updates.yml` reports stale or unknown pins; fetch
  failures keep its tracking issue open.
- `main-ci-failure-issue.yml` watches completed main runs of CI, Dependency
  update check, Digest lock PR sweep, Locked image check, PR branch cleanup,
  Publish ux images, Release, and Workflow lint; `pr-branch-cleanup.yml`
  keeps the branch list clean.

## Launcher-side verification

`UX_VERIFY_ATTESTATION` accepts `auto` (the default), `require`, or `off`.
Before pulling a lock-provided image, and on every `prewarm`, the launcher
uses `gh attestation verify` with the lock entry and publisher workflow.
`auto` prints one note and skips for an image override, missing attestation,
missing `gh`, or failed `gh auth status`; once verification starts, failure
or timeout prevents the pull. `require` makes skip conditions errors, while
`off` never verifies. Ordinary invocations do not re-verify a locally
present image, and `--warn` doctor paths never verify.

## CI runner network auditing

CI and image-publishing jobs use `step-security/harden-runner` in audit-only mode. It observes network egress without blocking requests; per-run insights are available in the GitHub Actions job summary.

## Digest-lock PR verification

The publisher dispatches `ci.yml` and `workflow-lint.yml` on the lock branch, then polls the authoritative required-check set for up to 30 minutes. Non-required failures do not block publishing; a concluded required-check failure or a PR closed without merge fails the job. A PR merged externally triggers the existing post-merge main workflows without waiting for their results. If required checks remain pending at the deadline, the publisher arms squash auto-merge with branch deletion and exits successfully so branch protection can complete the merge.

SPDX SBOM generation prefers the GHCR registry source, writes temporary data under the runner's temporary directory, and disables file metadata. A guard reports disk space and SBOM size immediately after generation and fails above 16 MiB, the attestation service's maximum.
