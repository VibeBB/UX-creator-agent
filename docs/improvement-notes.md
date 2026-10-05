# Improvement notes

This list records issues found during the VibeBB family refactor, what this
repository now addresses, and remaining cross-repository or product gaps.

## Addressed in UX-creator-agent

| Finding | Resolution |
| --- | --- |
| MCP tools had placeholder descriptions. | Every tool now has an explicit one-sentence description; coverage is checked in `tests/test_mcp_server.py`. |
| Record tool annotations did not distinguish append-only writes from idempotent calls. | Append-only record tools are marked non-idempotent; readers and deterministic writers use accurate MCP annotations. |
| Review records did not require findings for an applicable image. | Applicable reviews require findings; not-applicable reviews have a separate explicit path. |
| Production ownership used aliases that did not match sister plugin targets. | Owners now use `ux`, the ten registered sister target names, and `user`. |
| Liaison prompts and schemas covered only four sisters and were unbound to source changes. | SLP v2 supports all ten sister targets, workspace-relative SHA-256 inputs/artifacts, response evidence, and seven reconciled states. |
| Version bumps listed skill files in a fixed set. | `scripts/bump_version.py` discovers every `plugins/ux/skills/*/SKILL.md`; tests add a skill after fixture setup to cover discovery. |
| `AGENTS.md` described a smaller plugin family. | It now identifies all eleven repositories and documents the VRP and SLP v2 record paths. |

## Remaining

- Sister-side inbox and response handlers must be implemented and verified in
  each sister repository. This change defines the UX producer contract and
  registry only; it does not modify any other repository.
- UX storyboards and wireframes still lack a vision-review stage for rendered
  PNGs beyond the existing PlantUML-oriented path.
- UX import adapters remain limited to circuit, mechanical, wire, bard, and
  generic CSV inputs; other sister artifact formats need deliberate adapters.
- The slug expression currently lives in UX's sister registry and is not yet
  pinned as a family-wide protocol constant.

These remaining items are explicit follow-ups; they are not treated as
implemented or silently accepted by the liaison gates.
