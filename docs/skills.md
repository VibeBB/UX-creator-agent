# UX skills

Skills provide domain guidance to agents and are stored in
`plugins/ux/skills/*/SKILL.md`. Their keyword triggers help surface relevant
guidance; they do not run executable code or override deterministic gates.

| Skill | Purpose |
| --- | --- |
| `ux-cmf` | Author form language, palette roles, materials, finishes, parts, markings, and surface coverage. |
| `ux-contract-rules` | Path rule on `*.ux.json` / `*.ux.rb` — contract schema, id stability, and provenance reminders injected whenever a contract or DSL source is touched. |
| `ux-diagrams` | Understand Mermaid, PlantUML, XState, SCXML, Storybook requirements, and how Figma fits the generated projections. |
| `ux-interaction-content` | Map feedback records to LED, sound, haptic, motion, and text assets; request product sound cues from bard. |
| `ux-jtbd` | Write functional, emotional, and social jobs and calculate ODI opportunity scores. |
| `ux-persona` | Apply the UX designer voice, QCD discipline, and Think Different creed. |
| `ux-production` | Author production plans, dependencies, statuses, decisions, blockers, requests, and evidence loops. |
| `ux-ruby-style` | Write idiomatic UX Ruby DSL sources and compile them to contract JSON. |
| `ux-sibling-cooperation` | Import sister artifacts and coordinate hash-bound SLP v2 requests and responses. |
| `ux-theory-lenses` | Apply HIG, game design, JTBD/ODI, CJM/service blueprint, and QCD lenses to decisions. |
| `ux-workflow` | Run the conversational contract → gates → projections → advisory review workflow. |
| `ux-out-rules` | Path rule on `**/out/**` — generated projections are read-only; change the contract or plan and regenerate (the `protect-generated` hook enforces). |

## How agents should use skills

1. Select the skill that matches the current task, then follow its
   instructions and cited ADRs.
2. Keep authored knowledge in the contract or plan. Skills explain how to
   work; they are not project-specific evidence.
3. Regenerate projections and run gates after changing authored data.
4. When coordinating a sister request, follow `ux-sibling-cooperation` and
   the versioned protocol in [Sister cooperation](sister-cooperation.md).

The version bump utility discovers all skill files dynamically; adding a
directory under `plugins/ux/skills/` does not require maintaining a second
hard-coded list. The docs coverage test checks every discovered skill name.
