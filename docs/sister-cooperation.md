# Sister cooperation

UX-creator-agent coordinates with ten VibeBB sister targets through
workspace files and OpenHands task delegation. It does not import sister
Python packages or assume a live plugin-to-plugin API. The registered agent
and tool names below are the UX-side contract; each sister repository owns
the implementation of its inbox and response tools.

## Registered targets

| Target | Repository | Registered agents | Liaison agent | Expected inbox / response tools |
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

The family has eleven repositories including UX-creator-agent. Circuit's
registered agents include the two part-author agents; do not replace them
with guessed aliases.

## Request creation and delivery

A request file is `{id}.ux-request.json`, normally in a workspace liaison
directory. It has `schema_version: 2` and `system: "ux-creator"`, with:

- a unique normalized request `id`, `target_agent`, one of the six product
  `stage` values, `risk`, meaningful `purpose`, and optional `rationale`;
- nonempty `requested_changes`, `expected_deliverables`, and `acceptance`;
- workspace-relative `inputs` with SHA-256 hashes, optional `depends_on`
  request IDs, and timezone-aware `created_at`.

Inputs are hashed when the request is built. Paths must be normalized and
inside the workspace; traversal, absolute paths, and symlink escapes are
rejected. High-risk requests must cite an ID of a job declared in the UX
contract. `write_request` allows an identical repeat but refuses to replace a
different existing file unless `replace` is explicitly true.

The `ux-producer` and `ux-liaison` use OpenHands `task_tool_set` with the
deterministic brief from `ux_delegate`. The brief names the correct liaison
agent and passes the request ID, path, acceptance criteria, and expected
deliverables. It names the sister's own `<target>_record_decision` and
`<target>_record_impression` tools for VRP records; never direct a sister to
UX-only `ux_record_*` tools. The task call itself is not evidence that a
request was received or completed; the sibling response file is authoritative.

## Response and evidence

A response file is `{request-id}.ux-response.json` and carries the request
ID, registered `responder`, response `status`, reason, input hashes,
artifact paths/hashes, gate verdicts, VRP decision/impression event IDs,
questions for the user, and timezone-aware `responded_at`.

Response statuses are `accepted`, `in_progress`, `done`, `rejected`,
`deferred`, and `needs_info`. Conclusions other than accepted/in-progress
require a meaningful reason. A `done` response cannot cite failed or unknown
gate verdicts. Artifact hashes and input hashes are rechecked during
reconciliation.

## Liaison states

| State | Meaning |
| --- | --- |
| `open` | No valid response exists and all declared dependencies are answered. |
| `answered` | A response is present, from the target agent, and its inputs/artifacts/evidence reconcile. This describes record integrity; its response status may still be rejected, deferred, or needs-info. |
| `mismatched` | The response names a responder different from the request's target. |
| `stale` | The request's input hashes no longer match current workspace content. |
| `broken` | A present response has invalid or unavailable artifact/evidence references, or a `records_heads` chain head that is no longer in the responder's intact VRP log. Malformed JSON is separately listed in `malformed`. |
| `blocked` | No response exists and a dependency is missing or not in `answered` state. |
| `circular` | The request is part of a dependency cycle. |

Malformed request/response paths and orphan responses are listed explicitly;
they are never silently discarded. A malformed response with no usable
response does not count as answered. Dependency cycles are detected before
production uses the liaison view.

## Proposal triage and production

`ux propose` converts candidate changes to deterministic QCD triage. Eligible
proposals cite a declared job before they create requests; proposals with no
job link are held. Low-risk proposals can be sent automatically, while
high-risk proposals wait for a job-citing rationale. Bold proposals must name
the theory they break and serve an underserved job. Triage does not bypass
the explicit request replacement policy.

Production plans can link each workstream to a request. The production gates
check that linked requests exist, their target matches the workstream owner,
completed work has a `done` response, liaison evidence is not broken or
circular, and done responses cite decision and impression records. An
unavailable liaison directory or a missing response is `unknown`, not a
pass. See [Contracts](contracts.md) for the production plan format.

## Change control (ECR/ECO) and design review

A change to a hash-pinned file anywhere in the family goes through two
workspace records, authored by AI agents; no human approval step exists.

- `<id>.ecr.json` (`schema_version: vibebb.ecr/v1`, `ECR-<n>`): `origin`
  plugin, `reason`, `proposal`, `items[]` (`path`, `sha256` before the
  change), optional `raised_by` (the `ECO-<n>` whose result triggered it),
  `created_at`.
- `<id>.eco.json` (`vibebb.eco/v1`, `ECO-<n>`): the pinned `ecr`, `author`,
  `changes[]` (`path`, `before`, `after`, `gate_report` path+sha256) and
  `review` (`reviewers[]`, `findings[]` with `severity`
  blocker/major/minor, `disposition` open/fixed/accepted, `resolution`).

`ux change <eco>` / `ux_change_check` derives the impact itself: every JSON
object in the workspace holding one sha256 and one path to a workspace file
is a pin. The verdict passes only if every check passes:

| Check | Fails when |
| --- | --- |
| `eco.ecr` | the ECR changed after pinning or is invalid (`unknown` if missing) |
| `eco.scope` | an ECR item is not changed, or its `before` differs |
| `eco.applied` | a changed file is missing or its sha256 is not `after` |
| `eco.evidence` | the gate report changed or its `verdict` is not `pass` (`unknown` if missing or it does not cite the `after` sha256) |
| `eco.pins` | a consumer still pins an old sha256 of a changed file, or re-pinned without being listed in `changes` |
| `dr.independence` | the ECO author is one of its reviewers |
| `dr.findings` | a finding is open, a blocker is accepted rather than fixed, the resolution is missing, or the reviewer is not listed |
| `eco.cycle` | the `raised_by` chain of ECRs and ECOs loops |

Review findings come from an independent AI reviewer agent (for example a
sister's `*-review` agent briefed blind on the changed files). They can only
stop a change; the sister gates in `gate_report` decide whether it passes.

## Example files and scope

The `examples/smart-kettle/` and
`examples/smart-kettle-product/requests/` workspaces include v2 requests and
responses. The authoring smoke script copies these records into its output
workspace so the report's liaison lens exercises real examples.

This repository supplies the producer-side protocol, registry, and tests.
Inbox/respond implementation and end-to-end acceptance remain follow-up
work for each sibling repository; no other repository is modified here.
