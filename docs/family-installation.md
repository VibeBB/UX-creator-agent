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
MCP server names. The original lock is copied beside it. A failure is retained
and the other plugins are still assessed. The command exits 1 if any install
fails or the plugin lacks its declared MCP server or native liaison agent.
Existing output directories are refused to preserve earlier evidence.

Successful asset loading does not establish backend readiness or cooperation.
Next, use each installed plugin's documented launcher and digest-locked image
with attestation required. Confirm the selected launcher does not overlay host
source, initialize its MCP server, inspect tools, and exercise a hash-bound
request/response cycle. Record image digests, attestation results, invocations,
exit codes, output hashes and unresolved gaps separately. The installation
report keeps tool readiness, workflow completion and product acceptance unknown.

The historical lock deliberately preserves published versions rather than
substituting current main. In particular, Bard `v1.1.0` has no declared MCP
server. The verifier reports this gap and exits 1 even though the SDK can load
its agents. A later source checkout or tools image does not repair that
published-release claim; verify a new release independently when available.
