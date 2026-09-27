# ADR-0005: Experience loops, feedback records, and the game-design lens

- Status: Accepted
- Date: 2026-09-27

## Context

The contract already modeled journeys and statecharts, but had no way to
express two things the designer persona reasons about constantly:

1. **Feedback pairs** — every user action needs a perceivable response.
   Nielsen's response-time limits (0.1 s instant, 1 s uninterrupted flow,
   10 s attention boundary) give deterministic budgets: instant feedback
   ≤ 100 ms, uninterrupted flow ≤ 1 s, anything beyond 1 s requires a
   progress indicator, and > 10 s loses attention entirely.
2. **Experience loops** — the MDA/core-loop view of a product: a closed
   chain of actions that ends in a reward. Moment- and session-cadence
   loops that never close (no reward) are where engagement dies.

These are measurable, so they belong in the deterministic gate layer —
not in LLM judgement.

## Decision

Contract additions (all optional, `schema_version` unchanged):

- `StateDef`: `description`, `surface`, `entry[]`, `exit[]`
- `Transition`: `guard`, `actions[]`
- `Stage`: `kind ∈ {discover, onboard, use, recover, exit}`
- `feedback[]`: `{id, trigger, surface, modality, latency_ms,
  progress_indicator, description}`
- `loops[]`: `{id, steps[], reward, cadence}`

Deterministic gates (fail-closed):

- `statechart.*.deterministic` — same `(from,event)` requires distinct
  non-empty guards.
- `statechart.*.state_surface_declared` / `feedback.surface_declared` /
  `feedback.trigger_known` / `loop.steps_known` — referential integrity
  against declared surfaces, events, and touchpoints.
- `feedback.latency_budget` — Nielsen budgets: ≤1 s always allowed,
  1–10 s requires `progress_indicator`, >10 s fails.
- `loop.closes` — moment/session loops must declare a reward.
- `journey.onboarding_present` — app surfaces require an `onboard`
  stage; hardware-only products exempt.

`ux-report.json/.md` gains a **game-design lens** section with measured
numbers only (loop count/length, feedback coverage by modality, surfaces
without feedback, onboard/recover stage counts). It informs, never
verdicts.

Ruby DSL parity: `state`/`on`/`stage` gained the new keyword args;
`feedback` and `experience_loop` (`loop` collides with `Kernel#loop`)
were added.

## Consequences

- All fields are optional with defaults; `schema_version` stays 1 and
  every existing contract remains valid.
- The persona can argue "this loop doesn't close" or "this action has no
  feedback within 1 s" with deterministic evidence instead of opinion.
