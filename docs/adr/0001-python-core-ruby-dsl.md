# ADR-0001: Python core, Ruby as the design-expression runtime

- Status: Accepted
- Date: 2026-09-26

## Context

The sister repos (wire, mech, circuit, bard) implement every deterministic
entry point in Python and expose them through a stdio MCP server, a CLI,
and hook scripts that run on a Python-only OpenHands runtime. UX-creator
also wants Ruby in the product surface: the designer persona writes
idiomatic Ruby DSL to express UX contracts, and embedded-firmware UX
snippets target mruby.

## Decision

All executable logic is **Python 3.12** (`src/ux_creator/`): contract,
gates, projections, imports, requests, advisory, report, CLI
(`python -m ux_creator`), and `ux_creator.mcp_server`.

Ruby is a **design-expression runtime**, not the implementation
language: `ruby/lib/ux_dsl.rb` (+ `ruby/bin/ux-dsl`) is a plain-stdlib DSL
that prints the `.ux.json` contract; `ux_creator.ruby_bridge` runs `ruby`
as an unmodified subprocess (adapter) and validates the JSON into the
pydantic model. Missing ruby reports `unknown`, never a crash.
`mruby-check` runs `mrbc -c` for firmware-side snippets.

## Consequences

- Hooks and launcher stay byte-for-byte compatible with the sibling
  contract (Python on the host, docker-only execution inside ux-tools).
- The DSL cannot hide logic: it only constructs the contract shape; all
  judgement lives in `gates.py`.
