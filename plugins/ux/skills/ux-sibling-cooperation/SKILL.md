---
name: ux-sibling-cooperation
description: How ux-creator imports sibling-agent artifacts (circuit connectivity, mech envelope, wire contract, bard outputs) and issues ux-request.json change proposals.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - import connectivity
  - envelope
  - sibling
  - ux-request
  - 姉妹連携
  - 取り込み
---

# Sibling cooperation (ADR-0003)

Cooperation is JSON files in the shared workspace — never code imports.

## Inbound: `ux import <contract> --from <system> <file>`

Validates the file, records `{system, path, sha256, extracted}` in the
contract's `imports[]`, and extracts **touchpoint candidates only**:

| system | source artifact | extracted |
| --- | --- | --- |
| `circuit` | `*.connectivity.json` (circuit-agent) | connector `ref`s, housings |
| `mech` | `*.envelope.json` (mech) | anchor `name`s (clips, grommets) |
| `wire` | `*.contract.json` (wire-agent) | connector ids |
| `bard` | provenance/artifact JSON | artifact path strings |
| `csv` | generic JSON tables | first `id`/`ref`/`name` per entry |

The copy is the truth: re-import replaces the record; a missing file
makes the `imports.*` gate report `unknown`.

## Outbound: `ux request` → `<name>.ux-request.json`

```
{schema_version: 1, system: "ux-creator",
 target_agent: "wire|mech|circuit|bard",
 risk: "low|high", rationale: "...", requested_changes: [...]}
```

- **risk low** (colors, layout, copy, flow): may be delivered directly.
- **risk high** (tooling, board, firmware architecture): the CLI refuses
  unless `rationale` cites at least one declared job id — argue, never
  auto-send.
