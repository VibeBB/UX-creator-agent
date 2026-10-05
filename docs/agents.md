# UX agents

The six agents share the same deterministic UX core and workspace. Use the
specialist whose scope matches the requested work; delegate through the
OpenHands `task_tool_set` rather than inventing a plugin-specific task
transport. An agent's narrative is not a gate verdict.

| Agent | Use it for | Main outputs and boundaries |
| --- | --- | --- |
| `ux-creator` | End-to-end UX orchestration. Reframe a brief, maintain the contract, run gates, and coordinate projections and specialists. | Authored contract and derived UX outputs; asks for missing context rather than concealing it. |
| `ux-research` | Personas, functional/emotional/social JTBD, ODI opportunity scoring, journeys, and service blueprints. | Research structure for the authored contract; does not claim user research was performed when evidence is absent. |
| `ux-statechart` | Product behavior, states, events, transitions, guards, actions, and state-machine exports. | Statechart projections and gate results; authoring changes belong in the contract. |
| `ux-review` | Advisory vision review of rendered UX artifacts and image-intake touchpoints. | Typed findings tied to an image or event; never supplies a pass/fail verdict. |
| `ux-liaison` | Imports, SLP v2 requests, delegation briefs, response reconciliation, and user questions across all ten sisters. | Hash-bound workspace records; does not mark missing or stale evidence as complete. |
| `ux-producer` | Product/revision workstreams, dependencies, owners, blockers, decisions, sibling requests, and evaluation-to-revision flow. | Production plan and status projections; `production.*` gates determine readiness. |

## Tool and safety expectations

- Agents use the `ux` MCP server for deterministic validation, authoring,
  rendering, records, and liaison operations.
- The `ux-creator`, `ux-liaison`, and `ux-producer` agents have
  `task_tool_set` for specialist delegation. Other agents perform focused
  work within their authored files.
- Generated projections are protected from hand editing. Change the contract
  or plan and regenerate them.
- Use the relevant skill from `plugins/ux/skills/` for domain guidance. See
  [Skills](skills.md) for the complete list.
- Record user-approved choices and evidence with VRP tools. A prompt's
  recommendation does not become a decision unless it is selected and
  recorded.

Agent instructions are in `plugins/ux/agents/`. The docs coverage test checks
that every agent definition remains represented here.
