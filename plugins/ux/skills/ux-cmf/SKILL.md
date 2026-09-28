---
name: ux-cmf
description: Industrial design / CMF authoring — form language, palette roles, materials, finishes, per-surface parts, and markings in the UX contract's cmf block, with deterministic coverage and contrast gates.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - cmf
  - industrial design
  - color material finish
  - marking
  - 工業デザイン
  - 色・素材・仕上げ
---

# CMF block (ADR-0015)

```json
"cmf": {
  "form_language": "soft cylinder with a single warm-white light ring",
  "keywords": ["calm", "warm", "tactile"],
  "references": ["intake/mood-01.jpg"],
  "palette": [{"id": "porcelain", "name": "porcelain white", "hex": "#F4F1EA", "role": "primary"}],
  "materials": [{"id": "pp", "name": "PP (food contact)", "process": "injection molding"}],
  "finishes": [{"id": "soft_matte", "name": "soft matte", "gloss": "matte", "texture": "MT-11010"}],
  "parts": [{"id": "body_shell", "surface": "kettle_body", "color": "porcelain",
             "material": "pp", "finish": "soft_matte"}],
  "markings": [{"id": "wordmark", "surface": "kettle_body", "kind": "wordmark",
                "content": "VibeBB", "method": "pad_print", "color": "charcoal"}]
}
```

- Palette roles: `primary`, `secondary`, `accent`, `signal`, `neutral`;
  colors are `#RRGGBB`. Keep `signal` colors for status feedback.
- Gloss: `matte`, `satin`, `gloss`. Texture is a free code (e.g. a
  mold-texture spec).
- Marking kinds: `logo`, `wordmark`, `label`, `icon`, `regulatory`,
  `instruction`; methods: `print`, `pad_print`, `screen_print`, `laser`,
  `emboss`, `deboss`, `mold_in`, `sticker`.
- Every reference (surface, color, material, finish) must resolve —
  otherwise the contract is invalid.

## Gates (`cmf.*`)

- `cmf.part_coverage` — every `hardware`, `mechanism`, and
  `industrial_design` surface has a part.
- `cmf.primary_color` — the palette has a `primary` color.
- `cmf.marking_contrast` — a colored marking reaches 3:1 against every
  part color on its surface (WCAG non-text contrast); a marking on a
  surface with no part is `unknown`.

Appearance, mood, and brand fit stay advisory (`ux-review`). Material or
process changes that affect tooling are high-risk requests to `mech`.
The generated `<name>.cmf.md` is the CMF sheet handed to mech and
production engineering.
