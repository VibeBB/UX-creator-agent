---
description: Map feedback records to interaction content (LED, sound, haptic, motion, text), using bard cues for sound.
argument-hint: <contract.ux.json>
allowed-tools:
  - terminal
  - file_editor
---

Follow the `ux-interaction-content` skill. For product sounds, write a
`ux-request.json` to `bard` (target `bard`), have bard render
`cues/<slug>/cues.json` with `/bard:cue`, then
`python -m ux_creator import <contract> --from bard cues/<slug>/cues.json`.
Add one `content` asset per feedback record and run the gates until the
`content.*` checks pass; `author` regenerates `<name>.content.json` for
firmware and app teams.
