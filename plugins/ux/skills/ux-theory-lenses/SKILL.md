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

## Breaking theory on purpose

A `bold: true` proposal deliberately breaks an established guideline —
in the spirit of "Think Different": the rules exist because they usually
work, not because they always do. It is allowed only when all three
hold:

1. The proposal serves at least one **underserved** job — bold bets aim
   at unmet need, not novelty for its own sake.
2. `theory_break` names the theory/guideline being broken (e.g.
   "HIG/affordance: primary action must have a visible control") and why
   users will not miss the rule.
3. A job-cited rationale — bold proposals are always triaged as high
   risk.

Missing either → `needs_theory_break` or `bold_without_opportunity`
(both blocked, deterministic). Passing → `auto_send` with the rationale
prefixed `[bold] breaks: <theory_break> — ` so the sister agent sees the
intent.

## CJM / service blueprint

Frontstage actions the user sees, backstage processes they don't,
support processes beneath. Pain lives at the seams.

## QCD

Quality / cost / delivery is a triangle: pick two to lead, state the
third honestly in `qcd.rationale`.

## HIG numbers that are gates, not vibes

Two HIG/WCAG rules are enforced by `hig.*` gates on declared
`controls:`:

- **Target size**: button/touch/dial/switch controls with declared
  `size_mm` must be ≥ 7.8 mm on a side (44pt @163ppi). Undeclared
  dimensions are ignored — measure, don't guess.
- **Contrast**: a control with `fg`/`bg` must reach WCAG 4.5:1
  (3:1 when `large_text`), computed via relative luminance —
  `contrast_ratio(fg, bg)`.
