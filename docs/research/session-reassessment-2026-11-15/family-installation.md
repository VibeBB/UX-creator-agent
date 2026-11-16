# Pinned family installation and transport boundary

The [release lock](family-release-lock.json) fixes all eleven repository commits,
tags and plugin subdirectories. Installation is an asset check, not product
acceptance. Run the verifier in a new evidence directory:

```bash
uv run --group sdk-check python scripts/verify_family_install.py \
  --lock docs/research/session-reassessment-2026-11-15/family-release-lock.json \
  --out out/family-install-fresh
```

The verifier isolates SDK persistence, checks tag resolution, rejects symbolic
links before the SDK can dereference them, compares source and installed tree
digests, and retains a partial report after every plugin. An existing output
directory is rejected so a retry cannot erase a failed attempt. Do not edit a
lock or report to turn a failure into a success.

## Required entry points

Ten plugins, including UX, declare MCP servers. Bard intentionally has **no MCP
server**; its native transport is `scripts/bard_cli.py`. Installation checks for
Bard require `bard_cli.py`, `bard_liaison.py` and `bard_records.py` under
`scripts/`, as well as the declared liaison agent. A missing Bard MCP definition
is not an installation defect.

The clean fourth installation installed all eleven locked source trees and
returned exit 1: Bard v1.1.0 lacks those three native CLI assets. The earlier
reports incorrectly called this a missing MCP interface; they are retained as
failed assessments. The corrected run preserves that release gap without
inventing a server or borrowing another release's files.

Current-source Bard assets separately passed request → `in_progress` response →
changed-input `stale` detection. That result is not assigned to v1.1.0.
UX's corrected delegation instructions are in
[PR #208](https://github.com/VibeBB/UX-creator-agent/pull/208).

## Preparation and retry

Each inventory entry now includes the installed launcher's `preparation_command`
when one exists, and `next_steps` when installation or transport checks fail.
The command is a JSON argument array, so spaces in a path do not require shell
reconstruction. Run it only after checking local Docker availability and the
published image lock. Set the plugin's documented `*_VERIFY_ATTESTATION=require`
for the runtime checks; do not bypass a failed attestation or manufacture an
image pin. Document uses installed stdlib-only scripts and has no tools-image
prewarm requirement. Bard's missing CLI must be fixed by an actual verified
release, not by a prewarm command.

After correcting an installation/source/authentication error, rerun the verifier
with a **new** `--out` directory. Before comparing later tree digests, preserve
whether executing a stdlib script created `__pycache__` in an installed tree.
A source-to-install digest from a clean installation cannot silently be reused
after runtime files have been added. Runtime checks use
`PYTHONDONTWRITEBYTECODE=1` where supported.

## What the evidence establishes

- All eleven fixed plugins load as SDK assets.
- All ten MCP backends initialize and list their real tools; nine use published
  tools images with source overlays disabled, and Document uses installed scripts.
- Nine sister MCP transports pass SHA-bound request/acknowledgement/staleness
  checks. Responses deliberately remain `in_progress`, not `done`.
- The fixed Bard CLI transport remains unavailable. Current-source CLI success
  is recorded separately.
- `tool_readiness`, `workflow_completion`, `native_execution` and `acceptance`
  are separate. Asset loading leaves all four unknown. MCP initialization and
  protocol checks do not prove a native model completed a product workflow.

The [domain matrix](family-domain-validation.md) and
[evidence index](family-domain-validation.json) record runtime results and their scopes.
Physical devices, actual sound, native model image perception and end-user
acceptance remain unknown unless directly evidenced.
