# plugins/ux

OpenHands plugin assets for ux-creator-agent. The deterministic core lives in
`src/ux_creator`; everything here steers it — nothing here can pass a design.

- `skills/` — `ux_creator-workflow` (orchestration), `ux_creator-contract` (schema
  authoring), `ux_creator-gates` (repair loop), `ux_creator-connectivity` (imports),
  `ux_creator-contract-rules` (path-triggered rule injected when a
  `*.contract.json` / `*.intake.json` file is touched)
- `agents/` — task sub-agents: `ux_creator-brief` (intake conversation),
  `ux_creator-design` (author → gates loop), `ux_creator-review` (advisory). Each agent
  declares its own `hooks` because plugin-level hooks do not propagate to
  sub-agents; `ux_creator-review` omits `mcp_config` because it only reads files
  and images and drives no `ux_creator` MCP tools.
- `commands/` — `/ux_creator:design`, `/ux_creator:doctor`, `/ux_creator:gates`, `/ux_creator:export`
- `hooks/` — session doctor, `protect-generated` artifact guard, stop-time
  status report
- `.mcp.json` — registers the `ux_creator` stdio MCP server (thin wrapper over
  `src/ux_creator`)
- `scripts/ux_launcher.py` — resolves the `ux_creator` package matching the
  installed plugin and execs it inside the pinned `ux-tools` image
  (`docker run`), so every hook/MCP/CLI call runs against containerized
  dependencies; `python3 <launcher> <args>` mirrors `python -m ux_creator`
