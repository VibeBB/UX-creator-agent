# C3: preserve delivered revisions in observations

## Failure and correction

The producer identity foundation was verified at
`c7aa76019e475e05ea0acfd76a316754d01b4cbe`: the fast suite passed 706 tests,
SDK plugin loading passed, and the focused 22-test suite passed five times.
The latest review returned no open findings. These results describe that
source revision, independently of the historical cooperative sessions.

The observation hook still extracted filenames from every response string
and hashed files after tool return. Thus a withheld attachment could become
a claimed observation, and a later filesystem revision could replace the
bytes actually delivered. A failing regression run preserved both defects
before the hook changed.

The hook now hashes inline image content from the tool result. It matches
each delivered occurrence to `attached: true` metadata with the same digest;
text paths and withheld entries do not establish an observation. It supports
raw MCP image blocks and the SDK's `ImageContent.image_urls` data URLs,
without fetching remote URLs. Render, author, produce, and liaison-status
calls are observed, including the SDK's `ux_` server prefix.

Records retain `image_identity`, `identity_status`, the native observer
session, and call identity. Missing or unusable producer claims remain
`unknown`. A direct file-editor image view has unknown producer ownership.
The recorded SHA always describes returned bytes, including when the file
is overwritten or deleted before the hook runs. An image without usable
path metadata is retained with `image_path: null` and unknown identity;
the existing bounded Stop reports the unresolved review gap.

`delivery_evidence: inline_bytes` proves delivery at the tool boundary. It
does not establish model perception, review quality, or product acceptance.
Producer claims remain advisory rather than cryptographically authenticated.
Crop/tile ancestry, reviewer/source binding, and shared Stop ownership logic
still require implementation.

## Verification and reproduction

```bash
uv run pytest tests/test_image_observations.py tests/test_hooks.py tests/test_record_stop_scope.py -q
uv run python scripts/verify_all.py --stage fast
uv run --group sdk-check python scripts/check_plugin_load.py
```

An additional offline probe uses the installed SDK 1.62.0 MCP adapter and
file-editor executor. It checks returned revisions after file rewrites,
withheld images, and unassociated image bytes, five times each. Render output
is a deterministic double; no provider call or MCP process startup is
performed. Exact revisions, probe source, commands, failed attempts, and raw
logs stay in the private research evidence. The implementation PR records
final committed-source outcomes.
