# ADR-0003: Sibling cooperation via workspace JSON contracts

- Status: Accepted
- Date: 2026-09-26

## Context

ux-creator must read sibling-agent outputs (circuit connectivity, mech
envelope, wire harness contracts, bard artifacts) and send change
proposals back. OpenHands SDK v1.49.6 offers no typed plugin-to-plugin
API; the family already cooperates through JSON contract files in the
shared workspace (wire-agent ADR-0003).

## Decision

**Inbound** — `src/ux_creator/imports.py` validates a sibling file,
extracts touchpoint candidates only (connector refs/housings, envelope
anchors, connector ids, artifact paths), and records
`{system, path, sha256, extracted}` in the contract's `imports[]`. The
copy is the truth; there is no live coupling and no sibling code import.

**Outbound** — `src/ux_creator/requests.py` writes
`<name>.ux-request.json` `{schema_version: 1, system: "ux-creator",
target_agent, risk, rationale, requested_changes[]}`. `risk: low`
requests may be delivered; `risk: high` requests are refused by the CLI
unless the rationale cites at least one declared job id.

## Consequences

- ux-creator interoperates with wire, mech, circuit, and bard through
  files and `task` delegation only; it has no acd-agent dependency.
- Gate `imports.*` reports `unknown` when an imported file is absent —
  fail-closed.
