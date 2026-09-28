---
name: ux-production
description: Producer / orchestrator rules for the product-level <product>.production.json plan — stages, owners, dependencies, decisions, blockers, sibling request tracking, and the evidence loop back into design.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - production plan
  - producer
  - orchestrate
  - next actions
  - revision
  - 進行管理
  - プロデューサー
---

# Production plan (ADR-0015)

One plan per product revision: `<product>.production.json`. It is the
producer's only truth; `<product>.production-status.{json,md}` and
`<product>.production.mmd` are generated and must not be edited.

## Shape

```json
{
  "schema_version": 1, "system": "ux-creator",
  "artifact_kind": "ux_production_plan",
  "product": "smart-kettle", "revision": "rev-a",
  "goal": "one sentence the whole team optimizes for",
  "contract": "smart-kettle.ux.json",
  "workstreams": [{"id": "sound_cues", "stage": "design", "owner": "bard",
                   "deliverable": "...", "depends_on": ["ux_contract"],
                   "status": "done", "artifacts": ["cues/smart-kettle/cues.json"],
                   "request": "smart-kettle-cues"}],
  "decisions": [{"id": "pcb_vendor", "question": "...", "options": ["..."],
                 "status": "open", "blocks": ["pcb_order"]}],
  "blockers": [{"id": "drc", "workstream": "pcb_order", "description": "...",
                "status": "open"}],
  "evidence": [{"id": "cue_quiet", "workstream": "boil_bench",
                "observation": "...", "source": "bench/boil.csv",
                "feeds": ["rev_b_plan"]}]
}
```

- Stages: `requirements`, `design`, `manufacturing_handoff`, `build`,
  `evaluation`, `revision`.
- Owners: `ux`, `wire`, `mech`, `circuit`, `bard`, `doc`, `simulation`,
  `production-engineering`, `firmware`, `user`. Firmware and bench work
  have no dedicated agent yet — own them as `firmware` / `user`.
- Status: `todo`, `in_progress`, `blocked`, `done`.

## Gates (`production.*`, fail closed)

| Check | Fails when |
| --- | --- |
| `acyclic` | dependencies form a cycle |
| `stage_order` | a workstream depends on a later stage |
| `dependency_status` | `in_progress`/`done` before every dependency is `done` |
| `blockers_explained` | `blocked` without an open blocker/decision, or `done` with one |
| `done_has_artifacts` | `done` without artifacts, or an artifact is missing |
| `requests_answered` | `done` without an accepted sibling response (`unknown` without a liaison dir) |
| `evidence_loop` | evidence feeds a non-design/revision stage, its source is missing, or evaluation is done with no evidence |
| `ux_contract` | the linked UX contract fails its gates while a `ux` workstream is done (`unknown` otherwise) |

## Producer habits

- Decompose until each workstream has exactly one owner and one
  verifiable deliverable.
- Put trade-offs in `decisions` with options and ask the user; record
  the `decision` and `rationale` when decided.
- Measurements are evidence, not opinions: cite a file in the workspace.
- Start the next iteration by copying the plan to a new `revision`.
