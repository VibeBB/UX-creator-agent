# C3: advisory review delivery references and native selection limits

## Repository-local correction

The UX review writer now computes an `image_delivery` reference from the
existing `observations/ux/image-observations.jsonl` log. It checks the
observation's strict shape, canonical event digest and increasing sequence,
then requires the reviewer's own native session, resolved path and exact
returned-image SHA. A missing or unreadable log, malformed delivered record,
missing session, copied path or changed revision stays `unknown`.
Filename-only legacy records do not establish delivery. Repeated identical
deliveries leave the occurrence ambiguous and therefore `unknown`; the writer
does not choose an event on the model's behalf. Producer identity remains a separate
advisory claim; a file-editor delivery has unknown ownership. The review's
VRP event digest covers the computed reference. Input callers cannot assert it.

`scope: tool-return` is deliberately narrow. It does not establish perception,
review quality, native inspector source selection, or product acceptance.
Legacy reviews remain readable. Missing delivery does not reject an advisory
review or change a deterministic gate. Shared Stop policy still uses its
existing record obligations, including bounded unresolved gaps; consuming
delivery metadata in shared ownership policy and crop/tile lineage remain
separate unfinished work.

## Native inspector finding

The installed OpenHands inspector searches `MessageEvent(source="user")`
backwards for the latest user message containing `ImageContent`. MCP and
file-editor returns are `ObservationEvent` instances and are not searched.
`image_index` selects within that user attachment list. A question naming a
tool-returned path does not select that file, and the observation does not
return a selected-image SHA or source event ID.

The private deterministic probe at source
`457d81906bb05bb1e8f660bf19d9dff66291c972` exercised five cases five times:

| Conversation state | Native selection in all five repeats |
| --- | --- |
| File-editor image only | Error; no image selected |
| MCP image only | Error; no image selected |
| Older user image, newer tool image | Older user image |
| Older user image, newer text-only user message and tool image | Older user image |
| Explicit current user attachment | Current user image |

Environment: OpenHands SDK 1.62.0, OpenHands tools 1.62.0, MCP 2.3.0,
Python 3.14.10. The capture double counted selected URLs without calling a
provider. Provider calls: zero. MCP server startups: zero. Probe source SHA:
`169762c79c95153a4ff3890123ac32a419a1cf1c6ef42dd4f5600977e3a16920`.
Raw event fixtures and results remain private, separate from the historical
archive. No SDK or external repository was changed.
The installed inspector source SHA-256 was
`ac7350e3f62a16d75278e662e0a86cc585131cba0b55ade6817a40f6da8b512b`.

UX now marks successful native inspector events with
`source_image_status: unknown`. Reviewer instructions use inline tool images
with the configured multimodal profile and require unknown/not-applicable
when the image is unavailable. This documents a supported SDK path; it is
not evidence of actual model perception. No custom executor, transport,
event-history store, monkeypatch or new dependency was introduced.

## Verification boundary

The regression suite exercises real observation-hook output through the
review writer, explicit and inherited native sessions, producer ownership
separation, copied paths, rewritten/deleted revisions, corrupt logs, native
inspector-event metadata and VRP reference tampering. Verification uses:

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/test_image_observations.py tests/test_records.py tests/test_sdk_delegated_context.py -q
uv run python scripts/verify_docs.py
uv run python scripts/verify_all.py --stage fast
uv run --group sdk-check python scripts/check_plugin_load.py
```

Full committed-source results are recorded separately from working-tree
regressions. No GUI, provider vision, real audio or hardware result is
implied. Crop/tile ancestry, ownership policy consumption, finite checkpoint
resume and release-install acceptance remain open in the implementation plan.

At implementation commit `34507f3aa7e0af02e5acf41725063441f66abd54`, the
clean-tree verification passed all nine commands: fast verification with
752 tests, SDK plugin loading, both native probes, and five focused repeats
of 178 tests each. The native selection probe again produced all 25 expected
outcomes. Raw logs, source fixtures and command digests remain private;
[aggregate validation](review-image-delivery-validation.json) records the
source and reproducible command scope. These results do not close the
remaining C3/D or release-acceptance work.
