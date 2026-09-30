# ADR-0017: Development coverage gate

## Status

Accepted

## Context

The deterministic UX core needs a repeatable minimum test-coverage check in
the fast verification stage without adding test tooling to runtime installs.

## Decision

Add `pytest-cov==7.1.0` to the development dependency group only. The fast
verification stage runs pytest with coverage enabled and requires at least
77% statement coverage for `src/ux_creator`. Coverage is measured without
branch coverage; pytest defaults do not enable coverage.

## Consequences

Runtime users do not install pytest-cov. A test-suite change that drops
coverage below the threshold fails fast verification.
