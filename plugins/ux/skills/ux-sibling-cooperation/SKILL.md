---
name: ux-sibling-cooperation
description: How ux-creator imports sister artifacts and coordinates hash-bound SLP v2 requests with all ten VibeBB sisters.
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

# Sister cooperation (ADR-0003, SLP v2)

Cooperation uses workspace JSON files, hash-bound evidence, and the
registered sister task agents — never code imports.

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

## Sister registry

Requests target one of these ten plugins. When loaded, delegate to the
listed liaison agent with `task_tool_set`; use its inbox and response
tools. If the agent is unavailable, leave a request file in the shared
workspace and ask the user to open it in that plugin.

| Target | Sister repository | Registered agents | Liaison agent | Inbox / response tools |
| --- | --- | --- | --- | --- |
| `bard` | `bard-agent` | `bard`, `bard-cue`, `bard-critic` | `bard` | `bard_ux_inbox` / `bard_ux_respond` |
| `circuit` | `electrical-circuit-agent` | `circuit-brief`, `circuit-schematic`, `circuit-layout`, `circuit-library`, `circuit-review`, `circuit-part-author-a`, `circuit-part-author-b` | `circuit-brief` | `circuit_ux_inbox` / `circuit_ux_respond` |
| `dashboard` | `dashboard-agent` | `dashboard-architect`, `dashboard-developer`, `dashboard-review` | `dashboard-architect` | `dashboard_ux_inbox` / `dashboard_ux_respond` |
| `doc` | `document-agent` | `doc-liaison`, `doc-writer`, `doc-review`, `doc-launch` | `doc-liaison` | `doc_ux_inbox` / `doc_ux_respond` |
| `firmware` | `firmware-agent` | `firmware-architect`, `firmware-developer`, `firmware-review` | `firmware-architect` | `firmware_ux_inbox` / `firmware_ux_respond` |
| `fpga` | `fpga-agent` | `fpga-architect`, `fpga-developer`, `fpga-review` | `fpga-architect` | `fpga_ux_inbox` / `fpga_ux_respond` |
| `mech` | `mechanical-agent` | `mech-brief`, `mech-design`, `mech-review` | `mech-brief` | `mech_ux_inbox` / `mech_ux_respond` |
| `prodeng` | `production-engineering-agent` | `prodeng-liaison`, `prodeng-planner`, `prodeng-ftm`, `prodeng-review` | `prodeng-liaison` | `prodeng_ux_inbox` / `prodeng_ux_respond` |
| `sim` | `simulation-agent` | `sim-liaison`, `sim-analyst`, `sim-review` | `sim-liaison` | `sim_ux_inbox` / `sim_ux_respond` |
| `wire` | `wire-agent` | `wire-brief`, `wire-design`, `wire-review` | `wire-brief` | `wire_ux_inbox` / `wire_ux_respond` |

## Outbound: SLP v2 requests and responses

A request is a strict v2 JSON record named
`<id>.ux-request.json`. It binds each workspace-relative input path to a
SHA-256 and includes `schema_version: 2`, `system: "ux-creator"`, id,
target, product stage, risk, purpose, rationale, requested changes,
expected deliverables, acceptance criteria, dependencies, and a
timezone-aware creation time. Each input is an `{path, sha256}` pair.

Use `ux_request` or `python -m ux_creator request`; the result includes a
deterministic delegation brief. `ux_delegate` and `python -m ux_creator
delegate` rebuild that brief from an existing request. Differing request
files are not overwritten unless replacement is explicitly requested.
The brief names the sister's `<target>_record_decision` and
`<target>_record_impression` tools; do not direct sisters to UX-only
`ux_record_*` tools.

High-risk requests must cite at least one declared UX job id in
`rationale`. The proposal triage defaults hardware, mechanism, and
industrial design to `mech`; circuit to `circuit`; firmware to
`firmware`; and cloud, web, and app layers to `dashboard`. Circuit
proposals may explicitly target `wire`. High cost or slow delivery
escalates risk. Unknown surfaces/jobs, missing rationale, and other
blocked cases do not produce request files.

The target sister reads the request through its inbox tool and responds
through its response tool; never write response JSON by hand. The strict
v2 response binds each input hash observed by the sister and every
artifact path to SHA-256. It also records the responder, status, reason,
gate verdicts, VRP decision/impression event ids, user questions, and a
timezone-aware `responded_at`. Status is one of `accepted`,
`in_progress`, `done`, `rejected`, `deferred`, or `needs_info`. A `done`
response cannot contain a failing or unknown gate verdict.

## Reconciliation states

`python -m ux_creator liaison --workspace <workspace> --liaison-dir
<directory>` validates and reconciles files. It reports malformed
requests/responses and orphan responses rather than silently dropping
them.

| State | Meaning |
| --- | --- |
| `open` | No valid response has answered the request. |
| `answered` | A matching sister response is present and its evidence is valid. |
| `mismatched` | The response does not come from the requested target. |
| `stale` | A request input or the sister's observed input hash has changed. |
| `broken` | An artifact hash or referenced VRP event cannot be verified. |
| `blocked` | A declared dependency has not been answered. |
| `circular` | The request participates in a dependency cycle. |

Production plans can link workstreams to request ids and must assign the
matching target as owner. Production gates check request completion,
request ownership, liaison integrity, and sister-record evidence.
Projections include liaison rows, open user questions, and sister record
counts/freshness. A rejected or deferred high-risk answer is a design
signal: revisit the rationale or job framing instead of bypassing the
sister.
