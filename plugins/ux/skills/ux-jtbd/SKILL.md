---
name: ux-jtbd
description: Jobs-to-be-done and ODI opportunity scoring — how to write jobs, journeys, and the opportunity table.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - JTBD
  - jobs to be done
  - ODI
  - opportunity score
  - ジョブ理論
  - 顧客のジョブ
---

# JTBD / ODI

A job is progress a user seeks in a context, never a feature request.

Each `jobs[]` entry needs all three dimensions:

- **functional** — the practical task ("boil 500 ml in under 3 minutes")
- **emotional** — how they want to feel ("confidence it won't overflow")
- **social** — how they want to be perceived ("a tidy kitchen for guests")

`importance` and `satisfaction` are 1–10. The opportunity score
`importance + max(importance − satisfaction, 0)` is computed
deterministically (`*.odi.csv` projection, `elements.top_opportunities`
in ux-report.json) — never score by hand.

- score ≥ 15: underserved — attack here
- score ≤ 10: overserved — simplify or drop investment

Gate: every job must carry all three dimensions (`jobs.three_dimensions`).
