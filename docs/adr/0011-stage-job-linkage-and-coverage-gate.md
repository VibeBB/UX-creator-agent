# ADR-0011: Stage→job linkage and the opportunity coverage gate

- Status: Accepted
- Date: 2026-09-27
- Follows: ADR-0010 (which deferred the coverage gate for lack of linkage)

## Context

ADR-0010 computed `Job.served` but skipped `opportunity.coverage`
because no contract element referenced job ids. Without linkage an
underserved job can sit entirely outside the designed journey — the
exact failure ODI exists to catch.

## Decision

- `Stage.jobs: list[str]` — the job ids a stage advances. A
  model_validator rejects references to undeclared job ids
  (fail-closed). Additive; `schema_version` stays 1.
- `opportunity.coverage` gate: every underserved job must appear in at
  least one `stage.jobs`; detail lists `uncovered underserved: ...`.
- `opportunity.stage_links` companion check: `unknown` (warn, not fail)
  when the contract has jobs but no stage links any — keeps legacy
  contracts readable instead of silently passing coverage.
- `*.journey.mmd` gains `[jobs: a, b]` on section labels; `*.odi.csv`
  gains `covered_by` (`journey.stage` ids); `lenses.innovation` gains
  `coverage` and `uncovered_underserved`.
- Ruby DSL: `stage ..., jobs: %i[...]` — always emitted in `to_h`.

## Consequences

- The kettle example declares `boil`/`keep_warm` links across its
  stages; pair_app stays `jobs: []` (onboarding serves no scored job).
- The bold-proposal rule (ADR-0010) now composes with coverage: an
  underserved job both attracts bold proposals and demands stage
  coverage.
