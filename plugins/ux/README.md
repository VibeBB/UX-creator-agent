# plugins/ux

OpenHands plugin assets for UX-creator-agent. The deterministic core lives
in `src/ux_creator`; everything here steers it — nothing here can pass a
design.

- `skills/` — `ux-workflow` (orchestration), `ux-persona` (designer voice),
  `ux-theory-lenses` (HIG, game design, CJM, QCD), `ux-jtbd` (jobs + ODI),
  `ux-diagrams` (Mermaid/PlantUML/XState/SCXML/Storybook), `ux-ruby-style`
  (idiomatic Ruby DSL), `ux-sibling-cooperation` (imports + ux-request).
- `agents/` — task sub-agents: `ux-creator` (orchestrator persona),
  `ux-research` (JTBD/ODI/journey), `ux-statechart`, `ux-review` (vision
  advisory), `ux-liaison` (sibling requests). Every agent declares its own
  `hooks` and `mcp_config` because plugin-level hooks do not propagate to
  sub-agents.
- `commands/` — `/ux:doctor`, `/ux:discover`, `/ux:journey`,
  `/ux:statechart`, `/ux:review`, `/ux:propose`.
- `hooks/` — session_start `ux-doctor` (doctor `--warn`) +
  `intake-attachments` + `ensure-llm-profiles`; user_prompt_submit and
  stop `intake-attachments`; pre_tool_use `protect-generated` +
  `safety-rail`; stop `report-ux-status`; post_tool_use
  `record-vision-tool-event` + `record-image-observation`.
- `.mcp.json` — registers the `ux` stdio MCP server (thin wrapper over
  `src/ux_creator` via the launcher).
- `scripts/ux_launcher.py` — resolves the `ux_creator` package matching
  the installed plugin and execs it inside the pinned `ux-tools` image
  (`docker run`), so every hook/MCP/CLI call runs against containerized
  dependencies; `python3 <launcher> <args>` mirrors `python -m ux_creator`.
