# smart-kettle — product sound cues

- device: piezo
- cues: 4

| Cue | Purpose | UX feedback | Duration | Loop | Notes |
| --- | --- | --- | --- | --- | --- |
| `boot` | startup | — | 333 ms | no | c6 e6 g6 |
| `done` | completion | beep_done | 600 ms | no | g6 c7 |
| `overheat` | warning | — | 750 ms | yes | a6 r a6 r a6 |
| `press` | confirm | — | 83 ms | no | c7 |

## Rationale

A rising major arpeggio says the kettle is awake; a two-tone rising fourth closes the boil (the UX contract asks for a two-tone done chime); the overheat warning is a repeated single high pitch with gaps so it reads as urgent and never resolves; the press click is one very short high tick inside the 300 ms confirm budget. All pitches sit in the piezo band c5..c8.

## Sources

- ux_request: ux/smart-kettle.ux-request.json
- file: ux/smart-kettle.ux.json#feedback
