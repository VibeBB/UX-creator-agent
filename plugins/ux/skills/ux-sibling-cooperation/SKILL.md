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
| `bard` | provenance/artifact JSON, cue manifest `cues.json` | artifact path strings; `cue:<id>` per product sound cue |
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

## QCD triage: `ux propose` → `<name>.triage.json`

`python -m ux_creator propose --contract C --proposals P.ux-proposals.json
--out-dir out/` scores each change proposal deterministically and
auto-sends the safe ones as ux-requests.

| Surface layer | Risk | Default target |
| --- | --- | --- |
| hardware, mechanism, industrial_design | high | mech |
| circuit | high | circuit |
| firmware | high | — |
| cloud_backend, web_ui, smartphone_app, pc_app | low | — |

- `cost: high` or `delivery: slow` escalates any layer to high.
- Statuses (first hit wins): `unknown_surface` → `unknown_job` →
  `no_target` → `needs_rationale` → `auto_send`. Unknown surfaces fail
  closed (`risk: high`, no request file).
- Only `auto_send` proposals produce `*.ux-request.json`; high-risk ones
  still need a job-cited rationale. Proposals may override
  `target_agent` (must be a known sibling).

## Inbound: `<request-stem>.ux-response.json`

Sisters close the loop by writing a response beside the request:

```
{schema_version: 1, system: "ux-creator",
 request: "<request-stem>", responder: "circuit",
 status: "accepted|rejected|deferred|needs_info",
 reason: "...", artifacts: [...]}
```

`python -m ux_creator liaison --out-dir <dir>` reconciles requests and
responses (open / answered / mismatched responder, orphans, malformed —
listed, never fatal). A `rejected` or `deferred` **high-risk** request
is a design signal: re-open the proposal with a new rationale or reframe
the job itself — never bypass the sister by hand-editing her artifact.
Responses are informational only; they never touch the gate verdict.
