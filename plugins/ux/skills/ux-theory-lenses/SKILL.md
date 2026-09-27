---
name: ux-theory-lenses
description: Theory lenses for UX decisions — Apple HIG, game design (MDA, flow, core loop, feedback, onboarding, SDT), JTBD/ODI, CJM/service blueprint, QCD.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - HIG
  - game design
  - MDA
  - flow theory
  - self-determination
  - service blueprint
  - QCD
  - 理論
---

# Theory lenses

Apply these lenses when judging or proposing; cite them in rationales.

## Apple Human Interface Guidelines

Clarity, deference, depth. Content is the hero; UI chrome recedes.
Consistency, direct manipulation, feedback, metaphors, user control.

## Game design

- **MDA** — Mechanics → Dynamics → Aesthetics. Designers reason
  mechanics-first; players feel aesthetics-first. Check both directions.
- **Flow (Csikszentmihalyi)** — challenge vs skill balance; anxiety and
  boredom are both failures. Watch difficulty curves and friction.
- **Core loop** — the repeated action→reward cycle; every product has
  one. Model it in `loops[]` (steps = statechart events/touchpoints,
  reward, cadence); `loop.closes` fails unclosed moment/session loops.
- **Feedback** — every action deserves visible/audible/haptic response;
  silent systems erode trust. Model it in `feedback[]` (trigger, surface,
  modality, `latency_ms`, `progress_indicator`); Nielsen budgets are
  gated deterministically (`feedback.latency_budget`).
- **Onboarding** — teach inside the loop, not in a manual; first success
  in under a minute. Use stage `kind: "onboard"`; app surfaces without
  an onboard stage fail `journey.onboarding_present`.
- **Self-Determination Theory** — autonomy, competence, relatedness.
  Jobs map: functional ≈ competence, emotional ≈ autonomy, social ≈
  relatedness.

## JTBD / ODI

People hire products to make progress. Opportunity score =
importance + max(importance − satisfaction, 0); score ≥ 15 is underserved,
≤ 10 overserved.

## CJM / service blueprint

Frontstage actions the user sees, backstage processes they don't,
support processes beneath. Pain lives at the seams.

## QCD

Quality / cost / delivery is a triangle: pick two to lead, state the
third honestly in `qcd.rationale`.
