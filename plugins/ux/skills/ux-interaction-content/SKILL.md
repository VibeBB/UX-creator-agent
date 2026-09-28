---
name: ux-interaction-content
description: Interaction content — map each feedback record to concrete LED, sound, haptic, motion, or text assets; product sounds (startup, done, warning, confirm) come from bard cue sets rendered to MIDI/MML.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - interaction content
  - earcon
  - startup sound
  - LED pattern
  - haptic
  - 起動音
  - 完了音
  - 警告音
  - 演出
---

# Interaction content (ADR-0015)

`feedback` says *when* and *where* the product answers; `content` says
*what* it plays. Each asset realizes exactly one feedback record with
the same modality.

```json
"content": [
  {"id": "led_boil_breathe", "feedback": "led_boiling", "modality": "visual",
   "source": {"kind": "inline", "spec": "ring #E0632A breathe 1 Hz until boiled"},
   "loop": true},
  {"id": "cue_done", "feedback": "beep_done", "modality": "audio",
   "source": {"kind": "bard_cue", "ref": "cues/smart-kettle/cues.json", "cue": "done"},
   "duration_ms": 600}
]
```

Source kinds:

- `bard_cue` — audio only; `ref` is bard's `cues/<slug>/cues.json`,
  `cue` the cue id. Never compose melodies here.
- `file` — a workspace asset (`ref`), e.g. an animation or haptic file.
- `inline` — a short deterministic `spec` (LED pattern, vibration
  pattern, motion curve, notification copy).

## Product sounds through bard

1. `ux request <contract> --target bard --risk low --change "..."`
   listing each purpose (startup, completion, warning, confirm, error,
   pairing) and the feedback id it serves.
2. Bard renders the cue set with `/bard:cue` (MIDI + MML + provenance,
   original melodies only, device range piezo/speaker).
3. `ux import <contract> --from bard cues/<slug>/cues.json` — the import
   records the manifest hash and `cue:<id>` entries.
4. Reference the cue from a `bard_cue` asset.

## Gates (`content.*`, only when `content` is non-empty)

- `content.feedback_coverage` — every feedback record has an asset of
  its modality.
- `content.modality_match` — no asset disagrees with its feedback's
  modality.
- `content.bard_cue_imported` — every `bard_cue` resolves to a `cue:<id>`
  in an imported bard manifest; the `imports.*` checks then pin its hash.

`<name>.content.json` (generated) is the feedback → asset map firmware
and app teams implement. How good a sound or animation feels stays
advisory.
