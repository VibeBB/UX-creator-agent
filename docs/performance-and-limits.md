# Performance and limits

This plugin favors deterministic, auditable work over background services.
CLI operations and MCP calls invoke the same synchronous core operations;
there is no background queue or persistent database.

## Runtime and rendering limits

| Operation | Current bound |
| --- | --- |
| Ruby DSL subprocess | 60-second default timeout. |
| mruby syntax check | 30-second default timeout. |
| Mermaid render | 60-second default timeout per source/format. |
| PlantUML render | 60-second default timeout per source/format. |
| `render_all` | Processes sorted top-level `*.mmd` and `*.puml` files; default formats are SVG and PNG. It does not recursively scan subdirectories. |
| MCP inline images | Up to 8 rendered images, PNG/JPEG only, with a 4 MiB per-image limit. Oversized or unsupported images are not inlined. |
| Plugin image pull | The launcher uses bounded Docker inspection, attestation, and pull subprocesses; image pulls may wait up to 900 seconds. This is not an authoring-tool timeout. |

A timeout or missing external tool produces an explicit failure/unknown
render result; the report must not imply that an image was checked when it
was not. PNG rendering uses a 2× scale for Mermaid. Rendering cost therefore
depends on the number and complexity of generated diagrams and formats.

## Schema and workspace bounds

- Request IDs and protocol slugs are limited to 64 characters by the current
  literal expression `^[a-z0-9][a-z0-9._-]{0,63}$`.
- Request paths are normalized workspace-relative paths. Files outside the
  workspace, traversal components, and unsafe symlink paths are rejected.
- Request inputs, response artifacts, and VRP file evidence carry SHA-256
  hashes; directory evidence uses a deterministic tree digest.
- Request and response schemas are strict and frozen. Additional properties
  are rejected; there is no best-effort interpretation of unknown fields.
- Stage impressions require at least 400 characters and three distinct
  sentences.
- There is no documented contract-size, number-of-personas, or diagram-count
  service-level objective. Very large workspaces and huge rendered images
  should be split or simplified rather than assumed to fit an unlimited
  budget.

The slug expression permits underscores. It is the authoritative current
implementation even though nearby prose may describe the allowed alphabet
more narrowly; a future family-wide protocol decision should reconcile that
wording rather than silently change accepted IDs.

## Functional limits

- The import adapters currently cover circuit, mechanical, wire, bard, and
  generic CSV inputs. They extract touchpoint candidates, not complete
  engineering truth.
- Storyboard and wireframe PNG vision review beyond the existing
  PlantUML/render path is not a supported end-to-end product stage.
- Vision findings and stage impressions are advisory records, not product
  safety or accessibility certifications.
- The UX repository cannot guarantee that every sister inbox tool is
  installed or that a sister agent will respond. Missing sibling evidence is
  explicit in liaison and production status.
- The authoring host needs Docker and a resolvable digest-pinned
  `ux-tools` image for normal plugin execution and renders. There is no
  silent unpinned local-image fallback.

See [Operations](operations.md) for image resolution and verification
policies, and [Improvement notes](improvement-notes.md) for the prioritized
follow-up list.
