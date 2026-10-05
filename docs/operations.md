# Operations — UX-creator-agent

Release, dependency-update, and CI policy. Product documentation lives in
the README and `docs/`; design decisions live in `docs/adr/`.

## SBOM attestations

`publish-ux-images.yml` generates and attests a package-level SPDX-2.3 SBOM
for the published tools digest and uploads the full Syft SBOM as a 90-day
workflow-run artifact. The returned URL is stored as `sbom_attestation` and
verified by `locked-image-check.yml` when present;
an absent URL warns and continues.
The attested SBOM omits file entries and relationships involving files to
stay below the 16 MiB limit.

## Verification stages

`scripts/verify_all.py` gates every change:

- `docs` — markdown-only changes: verify_docs + git diff --check
- `fast` — ruff check, ruff format --check, pyright (strict), pytest,
  verify_docs, git diff --check
- `standard` — fast + `check_plugin_load.py` (SDK 1.52.0 plugin load) +
  locked-image e2e on `examples/smart-kettle` (`e2e_authoring.py`) +
  `check_ruby_dsl.py` inside the image
- `ruby` — Ruby DSL parity/lint/minitest inside the image only

### Partial runs and local image builds

`--list` dumps each stage's commands as JSON; `--group` (`lint`, `unit`,
`docker`), `--match <substr>`, and `--shard K/N` select a subset of a stage:

```bash
uv run python scripts/verify_all.py --stage fast --group lint
uv run python scripts/verify_all.py --stage fast --match test_contract
```

CI uses the same flags for its matrix legs, so a local partial run reproduces
a failing check exactly. Run the full `fast` stage before submitting.

Local `ux-tools` builds can reuse the CI-warmed registry buildcache; it is a
public `buildcache` tag, so no GHCR login is needed:

```bash
docker buildx build --load \
  -f docker/ux-tools.Dockerfile -t ux-tools:local \
  --cache-from type=registry,ref=ghcr.io/vibebb/ux-tools:buildcache \
  .
```

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
| openhands-sdk/-tools `1.52.0` | `pyproject.toml` sdk-check group |
| GitHub Action SHAs | `.github/workflows/*.yml` + `dependabot.yml` |
| Lynis audit version | `container-audit.yml` `git clone --branch` — `CISOfy/lynis` tags |

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
section by `scripts/bump_version.py`. Dispatching with `dry_run: true`
exercises the same version computation, CI verification, install smoke,
and artifact build while skipping the push/merge and `gh release create`
— the way to rehearse the pipeline without cutting a release. The
bump-version state machine — version resolution, tag check, direct push,
and the self-approving + dispatched-checks + auto-merge fallback PR —
lives in `scripts/release_bump.sh` (the workflow step is a thin wrapper)
and is covered by `tests/test_release_bump.py` (stubbed `gh`, local git
remotes).

`publish-ux-images.yml` accepts a `dry_run` dispatch input that rehearses
the publish: the ux-tools image builds into the local daemon and the
Trivy gate, SBOM chain, measurements, and smoke checks still run against
it, but nothing is pushed, promoted (`:latest`), attested, locked, or
dispatched, and no SARIF reaches code scanning. The run summary lists
every skipped step.

## CI hygiene

- `workflow-lint.yml` runs actionlint + zizmor on every workflow change.
- `locked-image-check.yml` fails PRs that drift the Dockerfile/lock and
  prewarms the pinned image through `ux_launcher.py` before running the
  shipped authoring example.
- `digest-lock-sweep.yml` retries merging stalled digest-lock PRs every 6
  hours and dispatches post-merge verification (CI + locked image check)
  on main after a successful merge, since a `GITHUB_TOKEN` merge does not
  trigger the push workflows itself.
- `check-dependency-updates.yml` reports stale or unknown pins; fetch
  failures keep its tracking issue open.
- `dependency-review.yml` requires the repository's **Dependency graph**
  feature (Settings → Advanced Security); sibling repos copying this
  workflow fail with "Dependency review is not supported on this
  repository" until it is enabled.
- `main-ci-failure-issue.yml` watches completed main runs of CI, Container
  hardening audit, Dependency update check, Digest lock PR sweep, Locked
  image check, PR branch cleanup, Publish ux images, Release, Scorecard,
  and Workflow lint; `pr-branch-cleanup.yml` keeps the branch list clean.

## Launcher-side verification

`UX_VERIFY_ATTESTATION` accepts `auto` (the default), `require`, or `off`.
Before pulling a lock-provided image, and on every `prewarm`, the launcher
uses `gh attestation verify` with the lock entry and publisher workflow.
`auto` prints one note and skips for an image override, missing attestation,
missing `gh`, or failed `gh auth status`; once verification starts, failure
or timeout prevents the pull. `require` makes skip conditions errors, while
`off` never verifies. Ordinary invocations do not re-verify a locally
present image, and `--warn` doctor paths never verify.

## Container hardening

Three layers were adopted after a comparative evaluation of Lynis,
`docker build --check`, Trivy, Grype, Dockle, and hadolint:

- **Dockerfile lint** (`dockerfile-lint` job in `ci.yml`): hadolint
  v2.15.1 via `hadolint-action` v3.5.0 plus `docker build --check`
  (BuildKit built-in). `.hadolint.yaml` allows only docker.io and
  ghcr.io registries and waives DL3008 (exact deb pins rot when archives
  drop them; downloaded tools are already version+sha256 pinned) and
  DL3066 (the `ux` account is intentionally named, uid 1000).
- **Image scan on publish** (`publish-ux-images.yml`): Trivy v0.75.0
  via `trivy-action` v0.36.0 scans the pushed digest for
  CRITICAL/HIGH fixable vulnerabilities, secrets, and misconfiguration,
  gated (`exit-code 1`), with SARIF uploaded to code scanning
  (`category: trivy-ux-tools`) and a full JSON report as an artifact.
  The action is SHA-pinned and `version:` is explicit — the March 2026
  Trivy supply-chain compromise made both non-negotiable.
- **Weekly audit** (`container-audit.yml`, Mondays 03:57 UTC): pulls the
  pinned digest from `docker/image-digests.json`, re-scans with a fresh
  vulnerability DB (new CVEs against the frozen image), runs the Docker
  CIS compliance report, runs an informational in-image Lynis 3.1.7
  audit, aggregates `container-hardening.json` (artifact), and
  edits/creates a "Container hardening report" issue. The issue closes
  automatically when fixable HIGH/CRITICAL findings reach zero. The
  Lynis Hardening Index is recorded as a trend metric only — its
  denominator shifts with container-skipped tests, so it never gates.

Not adopted, with reasons: `lynis audit dockerfile` (~6 greps, frozen
since 2018, subset of hadolint, hardening index always 1);
Dockle (v0.4.15 stale; its CIS-derived checks are covered by Trivy's
`--compliance docker-cis` report); Grype (equivalent for the SBOM path,
kept as fallback); checkov (redundant third linter); `cisofy/lynis`
Docker image (does not exist — Lynis runs from a pinned git clone);
non-root USER enforcement and HEALTHCHECK enforcement (CI tools images —
deferred policy decisions).

Changelog evaluation for the adopted pins is in the introducing PR.
Suppressions: `.hadolint.yaml` waivers above; `.trivyignore` holds
time-boxed finding IDs — entries must carry an `exp:` date and a
rationale line here when added.

The uv-managed CPython's bundled `pip` payload (vendored urllib3,
msgpack, setuptools — never invoked; dependencies install via `uv` and
the shipped venv is pip-less) is stripped in the `uv python install`
layer, so the publish gate stays clean without `.trivyignore` waivers.

Other CVE-driven image surgery: the base image's default `json` gem
ships its gemspec and stdlib copies that shadow updates, so the gem
layer removes every 2.18.x trace before installing the pinned release;
base-image Debian packages that carry a released fix (e.g.
`libpcre2-8-0`) are listed in the apt install layer so they upgrade —
the digest-pinned base never self-updates.

The weekly audit runs Lynis as the image's unprivileged `ux` user —
`tests/test_workflow_paths.py` requires every workflow `docker run
--user` to be `ux` — so kernel- and account-level tests are skipped and
the index reads lower; that is acceptable for a trend-only audit.

### CIS baseline

The Trivy CIS compliance scan reports `DS-0002` (image runs as root) and
`DS-0026` (no `HEALTHCHECK`) on every tools image. Both are waived with
`exp:` entries in `.trivyignore`: these are CI build/tool containers, not
deployed services — workflows that need a non-root UID already run the
image with `docker run --user`, and batch tooling has no health endpoint
to probe. The waivers renew or get re-fixed by Dockerfile changes when
they lapse.

## CI runner network auditing

CI and image-publishing jobs use `step-security/harden-runner` in audit-only mode. It observes network egress without blocking requests; per-run insights are available in the GitHub Actions job summary.

## Digest-lock PR verification

The publisher dispatches `ci.yml` and `workflow-lint.yml` on the lock branch, then polls the authoritative required-check set for up to 15 minutes. Non-required failures do not block publishing; a concluded required-check failure or a PR closed without merge fails the job. A PR merged externally triggers the existing post-merge main workflows without waiting for their results. If required checks remain pending at the deadline, the publisher arms squash auto-merge with branch deletion and exits successfully so branch protection can complete the merge.

SPDX generation prefers the GHCR registry source, writes temporary data under
the runner's temporary directory, and disables file metadata. The publisher
removes file entries and relationships involving files to produce the
package-level SPDX-2.3 SBOM. A guard reports disk space and the attested SBOM
size after transformation and fails above 16 MiB; the full Syft SBOM is
uploaded as a 90-day workflow-run artifact.

## Settings-level posture (recorded decisions)

The following live in repository Settings rather than code; they are
intentional for the solo-maintainer bot-merge workflow and are recorded
here so audits do not re-flag them:

- Branch protection does not require approving reviews, code owners, or
  "apply to administrators": every merge is performed by automation
  (digest-lock, version-bump, and Devin PRs), so required approvers would
  only add friction to a pipeline that already gates on the required-check
  set. OpenSSF Scorecard reports this as Branch-Protection 3 and
  Code-Review 0; that is the recorded trade-off, not an oversight.
- The Dependency graph must stay enabled for `dependency-review.yml` to
  evaluate pull requests.
- `release.yml` is dispatch-only; run it once with `dry_run=true` before
  the first real release to rehearse bump, verify, and install-smoke
  without creating a GitHub release.
