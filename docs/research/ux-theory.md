# UX theory lenses — research summary

Condensed references the plugin's skills and gates draw on. Each maps to
a contract element or gate.

## Jobs to be done (JTBD) and ODI

Users "hire" a product to make progress in a context; the requested
feature is a hypothesis, the job is the truth. Every job decomposes into
**functional**, **emotional**, and **social** dimensions — the gate
`jobs.three_dimensions` enforces all three.

Outcome-Driven Innovation scores opportunity as
`importance + max(importance − satisfaction, 0)` on 1–10 scales:
≥ 15 underserved, ≤ 10 overserved. The contract stores raw scores; the
`*.odi.csv` projection sorts jobs by opportunity.

## Customer journey maps and service blueprints

A journey is ordered stages with touchpoints and an `emotion` score
(1–5). Stages at emotion ≤ 2 must record a `pain_points[]` entry — pain
without a recorded cause is unauditable (gate
`journey.*.pain_points_recorded`). A service blueprint separates
frontstage (visible), backstage (invisible), and support processes;
failures concentrate at the seams.

## Apple Human Interface Guidelines

Clarity, deference, depth; consistency, direct manipulation, feedback,
metaphors, user control. Used as review heuristics in `ux-review`, never
as gates.

## Game design lenses

- **MDA**: mechanics → dynamics → aesthetics; designers and players read
  the loop in opposite directions.
- **Flow**: challenge/skill balance; friction and boredom both show up
  as journey emotion dips.
- **Core loop**: the repeated action→reward cycle a product must make
  explicit. The contract's `loops[]` records it: `steps` (statechart
  events or stage touchpoints), `reward`, `cadence`; the `loop.closes`
  gate fails moment/session loops with no reward.
- **Feedback**: every action needs a response — silent transitions are
  where trust leaks. `feedback[]` pairs a `trigger` with a `surface`,
  `modality`, and `latency_ms`; `feedback.latency_budget` enforces
  Nielsen's response-time limits (≤1 s fine, >1 s needs a
  `progress_indicator`, >10 s always fails).
- **Onboarding**: teach inside the loop; first success in under a minute.
  Stage `kind: "onboard"` marks it; `journey.onboarding_present` fails
  when app surfaces exist without one.
- **Self-Determination Theory**: autonomy/competence/relatedness ≈ the
  JTBD emotional/functional/social split.

## QCD

Quality–cost–delivery is a fixed triangle. The contract's `qcd` block
records the chosen stance plus `rationale`; `core_experience` (never
compromised) is separated from `implementation_spec` (negotiable).
