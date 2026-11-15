# C3: image identity at the MCP boundary

## Problem and implementation

The earlier observations identified images by paths and current hashes.
Neither a directory name nor the plugin returning an attachment establishes
its producer. A sister's image returned by UX must retain the sister's
identity. A hash calculated only at return time also fails to show that
bytes changed after the renderer or SLP response claimed them.

`RenderResult.image_identity` now carries a frozen, strict `ImageIdentity`:
resolved `path`, `sha256`, `owner_plugin`, and `origin`. A successful UX
render captures these fields from the output with owner `ux`. Failed or
unreadable output remains `unknown`. Liaison images instead carry the
validated SLP responder and the artifact's declared SHA. The attachment
reader compares the entire validated response with the scanned entry's
canonical `response_sha256`. Changing artifacts, input hashes, gate evidence,
or any other response field cannot reuse that entry's earlier `answered`
state. JSON whitespace or key order does not change the fingerprint.

At attachment time MCP hashes the actual bytes and compares both digest and
resolved path with the producer claim. Metadata reports `bound`, `unknown`,
or `mismatch`; mismatched images are withheld without consuming the inline
image cap. The expected claim and actual digest remain visible for diagnosis.
Legacy render results without producer metadata stay `unknown`, even when
their filenames look like a known plugin's output.

## Verification scope

Focused regressions cover renderer output identity, same-stem Mermaid and
PlantUML outputs, unreadable output, responder ownership despite a UX-looking
filename, changed response identity, changed image bytes, equal bytes at a
different path, unknown legacy ownership, and the existing inline size/count
limits. A pre-fix regression reproduced replacement artifacts inheriting an
earlier `answered` state; the complete-response fingerprint closes that gap.
Commands:

```bash
uv run pytest tests/test_render.py tests/test_mcp_inline_images.py -q
uv run python scripts/verify_all.py --stage fast
uv run --group sdk-check python scripts/check_plugin_load.py
```

Revision-bound outcomes are recorded in the implementation PR and private
verification evidence. The pre-update metadata expectations and an initial
new-test workspace setup error are retained as failed attempts in that
private evidence; neither is counted as a successful check.

These checks use deterministic renderer doubles and MCP content blocks.
They do not establish actual renderer/image compatibility, visual quality,
LLM inspection, GUI behavior, or product acceptance.

## Remaining C3 work

This is producer and delivered-image identity, not a completed image-lineage
protocol. Explicit crop/tile parent revisions, multiple-source lineage,
reviewer/source revision binding, and shared Stop ownership logic still need
implementation. [Observation propagation](image-observation-delivery.md)
preserves returned bytes and producer claims at the hook boundary. A producer claim is
advisory metadata; it is not cryptographic authentication. Existing artifact
review obligations and deterministic gate verdicts remain unchanged.
