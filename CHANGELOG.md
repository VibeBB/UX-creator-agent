# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added (phase 11)

- `controls:` contract list — physical/app controls with surface,
  kind, optional `size_mm`, `fg`/`bg` `#RRGGBB` and `large_text`;
  fail-closed validators (unknown surface/touchpoint, partial colors).
- `hig.*` gate group: `hig.target_size` (≥7.8 mm ≈ 44pt) and
  `hig.contrast` (WCAG 4.5:1, 3:1 for large_text) — real verdict gates.
- Projections: `{name}.mindmap.mmd`, `{name}.{journey}.sequence.puml`,
  `{name}.wbs.puml`. ADR-0014.

### Fixed

- `*.journey.mmd` section labels no longer carry the `[jobs: …]` suffix
  (invalid Mermaid journey syntax — parse error); jobs now ride the
  task line as `(jobs: a, b)` after the touchpoints.
- `*.wireframe.puml` Salt frames are balanced (`{+ … }`) and empty
  inner blocks get a `.` placeholder — PlantUML no longer crashes.

### Added (phase 10)

- Service-blueprint PlantUML projection `{name}.blueprint.puml` (Customer
  journey lane + Frontstage/Backstage/Support swimlanes) when the
  contract declares `service_blueprint`; per-journey CJM emotion curve
  `{name}.{journey}.emotion.mmd` (Mermaid `xychart-beta`) plus
  `{name}.{journey}.emotion.json` data. ADR-0013.

### Added (phase 8)

- `Stage.jobs` links stages to the jobs they advance (fail-closed
  validator against declared job ids; Ruby DSL `stage ..., jobs:`).
- `opportunity.coverage` gate fails on uncovered underserved jobs;
  `opportunity.stage_links` fails when jobs exist but
  no stage links any
  (legacy contracts warn). `*.odi.csv` gains `covered_by`;
  `*.journey.mmd` labels stages with `[jobs: ...]`;
  `lenses.innovation.coverage`/`uncovered_underserved` in ux-report.
  ADR-0011.

### Added (phase 7)

- Innovation lens: `Job.served` (underserved/appropriate/overserved),
  `served` column in `*.odi.csv`, `lenses.innovation` in ux-report
  (by_served, bold_proposals, bold_blocked, core_experience).
- Bold proposals: `bold`/`theory_break` fields; blocked statuses
  `needs_theory_break` and `bold_without_opportunity`; bold auto-send
  forces high risk and prefixes the request rationale with
  `[bold] breaks: <theory_break> — `. ADR-0010.

### Added (phase 6)

- Sister response contract: `responses.py` + `liaison` CLI +
  `ux_liaison_status` MCP read tool reconcile `*.ux-request.json` with
  `*.ux-response.json` (open/answered/mismatched, orphans, malformed);
  `lenses.liaison` section in ux-report (requests, by_status,
  rejected_high_risk). Example response for smart-kettle; e2e copies
  sibling responses into out_dir before the report. ADR-0008,
  ADR-0009 (mmdr evaluation — not adopted).

### Added (phase 5)

- Advisory reconciliation: `reconcile_findings` checks review-visual
  findings against contract + gate truth (corroborated/contradicted/
  unverifiable); `review-reconcile` CLI + `ux_review_reconcile` MCP
  read tool; `lenses.review` section in ux-report (records, malformed,
  severity/reconciliation counts, images without records). Verdict stays
  gate-only. ADR-0007.

### Added (phase 4)

- `proposals.py` + `ux propose` / `ux_propose`: deterministic QCD triage
  of `*.ux-proposals.json` — layer-based risk, statuses
  (`auto_send`/`needs_rationale`/`no_target`/`unknown_job`/
  `unknown_surface`), `<name>.triage.json` output, auto-emitted
  ux-requests for `auto_send` proposals. Example proposals file for
  smart-kettle; e2e runs propose when the file sits next to the
  contract. ADR-0006.

### Added (phase 3)

- Richer statecharts: `description`/`surface`/`entry`/`exit` on states,
  `guard`/`actions` on transitions; XState/SCXML/Mermaid/PlantUML
  projections emit them.
- `feedback[]` and `loops[]` contract models + deterministic gates
  (`deterministic`, `state_surface_declared`, `surface_declared`,
  `trigger_known`, `latency_budget` Nielsen budgets, `steps_known`,
  `closes`, `onboarding_present`).
- `<name>.experience-loops.mmd` projection; Storybook `states`/
  `feedback` requirements; `lenses.game_design` measured section in
  `ux-report.json/.md`.
- Ruby DSL parity: `experience_loop`, `feedback`, new `state`/`on`/
  `stage` kwargs. ADR-0005.

### Added

- Initial scaffold: `src/ux_creator` Python core (contract, gates,
  projections, imports, requests, advisory, report, render, doctor,
  ruby_bridge, cli, mcp_server) — the 5th VibeBB sibling.
- Ruby design-expression DSL (`ruby/lib/ux_dsl.rb`, `ruby/bin/ux-dsl`)
  emitting `.ux.json` contracts; `mruby-check` via `mrbc -c`.
- Plugin `plugins/ux`: 5 agents, 6 commands, 7 skills, 8 hooks, launcher,
  MCP server (`ux_doctor`, `ux_validate_contract`, `ux_gates`,
  `ux_author`, `ux_from_ruby`, `ux_import`, `ux_request`,
  `ux_mruby_check`, `ux_render`).
- `docker/ux-tools.Dockerfile`: ruby:4.0.7-slim-trixie base, uv 0.12.19,
  Semeru OpenJ9 JRE 27, PlantUML MIT jar, mruby 4.0.0, mermaid-cli,
  Chromium, rubocop+minitest — all sha256/apt pinned, non-root `ux`.
- Deterministic gates: statechart (single initial, reachability, defined
  events, no dead ends), journey surfaces/pain-point accounting, JTBD
  three-dimension, core-experience non-empty, imports sha256 —
  fail-closed `unknown`.
- Projections: Mermaid journey + statechart, PlantUML state + Salt
  wireframe, XState v5, SCXML, Storybook stories, ODI CSV, manifest +
  provenance, `ux-report.json/.md`.
- Sibling cooperation: copy-in imports (circuit connectivity, mech
  envelope, wire harness, bard artifacts) and `ux-request.json` writers
  with high-risk job-id rationale enforcement.
- Examples: `examples/smart-kettle` (`.ux.rb` source + committed
  `.ux.json`, parity-tested).
- Full wire-mirrored workflow set, scripts, and docs (operations,
  ADR-0001..0004, research notes).
