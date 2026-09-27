# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
