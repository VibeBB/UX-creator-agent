# Repository memory — UX-creator-agent

- Python 3.12 core (`src/ux_creator/`); Ruby is only a DSL expression
  runtime (`ruby/lib/ux_dsl.rb`) — all judgement lives in `gates.py`.
- Every UX entry point is `python -m ux_creator <cmd>` inside the locked
  `ux-tools` image; the host never runs mmdc/plantuml/mrbc.
- Contracts: `{product}.ux.json` with `schema_version:1`,
  `system:"ux-creator"`; gates are fail-closed (`unknown` never passes).
- Sibling cooperation is workspace JSON only — imports are copy-in with
  sha256, requests are `<name>.ux-request.json`; high-risk needs a job id.
- Generated projections (`out/`, manifest/provenance/report) are
  hook-protected — re-derive, never hand-edit.
