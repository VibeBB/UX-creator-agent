# Verify a fixed family installation

Run the native SDK installer against an immutable eleven-plugin release lock
in a **new evidence directory**:

```bash
uv run --group sdk-check python scripts/verify_family_install.py \
  --lock docs/research/session-reassessment-2026-11-15/family-release-lock.json \
  --out out/family-installation
```

The lock records each published tag, repository, plugin subdirectory and full
source commit. The verifier rejects sources outside the registered VibeBB
family, moving refs, tag/commit mismatches, duplicate or missing family entries,
and symlinks in fetched source or installed assets. Source links are checked
before the SDK copies and dereferences them; installed bytes must then match
the checked source digest. It uses a fresh `OH_PERSISTENCE_DIR`, leaves
the normal SDK installation untouched, and does not replace `HOME`.

Each completed installation is appended to `report.json` with the resolved
source commit, manifest version, installed asset digest, agents, commands and
MCP server names, available preparation command arrays and recovery steps.
The original lock is copied beside it. A failure is retained and the other
plugins are still assessed. The command exits 1 if any install fails or the
plugin lacks its declared MCP server, native CLI assets or liaison agent.
Existing output directories are refused to preserve earlier evidence.

Successful asset loading does not establish backend readiness or cooperation.
For Docker-based sisters, use the installed launcher and digest-locked image
with attestation required and host source overlays disabled. Document uses
installed stdlib scripts and needs no image prewarm. Initialize declared MCP
servers and inspect their real tools; Bard instead uses its native SLP CLI.
Exercise a hash-bound request/response cycle. Record image digests where
applicable, attestation results, invocations,
exit codes, output hashes and unresolved gaps separately. The installation
report keeps tool readiness, workflow completion and product acceptance unknown.

The historical lock deliberately preserves published versions rather than
substituting current main. Bard intentionally has no MCP server. Its pinned
`v1.1.0` release lacks `bard_cli.py`, `bard_liaison.py` and `bard_records.py`;
the verifier reports those missing CLI assets and exits 1 even though the SDK
can load its agents. A later source checkout or tools image does not repair
that published release; verify a new release independently when available.
See the [preparation and retry procedure](research/session-reassessment-2026-11-15/family-installation.md)
and [domain evidence matrix](research/session-reassessment-2026-11-15/family-domain-validation.md)
for recorded scopes and limitations.
