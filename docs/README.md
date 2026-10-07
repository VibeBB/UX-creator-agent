# ux-creator-agent documentation

Documentation for the VibeBB UX design plugin. The root README is the
product overview; this directory contains the architecture, user workflow,
protocols, operations, and accepted design decisions.

## Product and technical guides

- [Architecture](architecture.md) — system boundaries, execution flow, and core entry points
- [Workflow](workflow.md) — brief-to-contract, gates, review, evidence, and handoff
- [Agents](agents.md) — all UX specialist agents and their boundaries
- [Skills](skills.md) — all UX knowledge skills and when to use them
- [Commands](commands.md) — CLI and OpenHands slash commands
- [MCP](mcp.md) — tools, schemas, effects, outputs, and errors
- [Hooks](hooks.md) — lifecycle events, scripts, and record policy
- [Contracts](contracts.md) — UX, SLP v2, production, VRP, and advisory formats
- [Records and vision](records-and-vision.md) — decision, impression, image, and review evidence
- [Sister cooperation](sister-cooperation.md) — ten registered targets and hash-bound exchange
- [Performance and limits](performance-and-limits.md) — timeouts, inline image caps, and known gaps
- [Development](development.md) — checkout setup and prescribed verification
- [Test coverage and test design](test-coverage.md) — C0/C1/C2/MCC/MC/DC and boundary coverage, floors, test-design techniques
- [Improvement notes](improvement-notes.md) — resolved findings and maintainer follow-ups
- [Operations](operations.md) — releases, dependency updates, Docker image, and CI policy
- [Dependency updates](dependency-updates.md) — pinned versions, sources, and adoption decisions

## Research

- [UX theory lenses](research/ux-theory.md) — JTBD/ODI, CJM, service blueprint, HIG, game design
- [Ruby idioms](research/ruby-idioms.md) — the DSL's style contract
- [SDK v1.50.0 feature evaluation](research/sdk-v1.50.0-feature-evaluation.md) —
  OpenHands SDK and uv update decisions
- [SDK v1.50.1 feature evaluation](research/sdk-v1.50.1-feature-evaluation.md) — OpenHands SDK/tools adoption decisions
- [SDK v1.51.0 feature evaluation](research/sdk-v1.51.0-feature-evaluation.md) — OpenHands SDK/tools and uv 0.12.22 adoption decisions
- [SDK v1.52.0 feature evaluation](research/sdk-v1.52.0-feature-evaluation.md) — OpenHands SDK/tools adoption decisions
- [SDK v1.53.0 feature evaluation](research/sdk-v1.53.0-feature-evaluation.md) — OpenHands SDK/tools adoption decisions
- [Agent Canvas v1.25 feature evaluation](research/ac-v1.25-feature-evaluation.md) — Agent Canvas / OpenHands platform adoption decisions

## Accepted ADR list

- [ADR-0001](adr/0001-python-core-ruby-dsl.md) — Python core, Ruby expression runtime
- [ADR-0002](adr/0002-ruby-slim-base-and-openj9.md) — ruby slim base image + Semeru OpenJ9 JRE
- [ADR-0003](adr/0003-sibling-cooperation-via-contracts.md) — sibling cooperation via workspace contracts
- [ADR-0004](adr/0004-plantuml-mit-and-tool-licenses.md) — PlantUML MIT jar and tool license policy
- [ADR-0005](adr/0005-experience-loops-and-feedback-lens.md) — experience loops, feedback records, game-design lens
- [ADR-0006](adr/0006-qcd-triage-of-proposals.md) — QCD triage of change proposals
- [ADR-0007](adr/0007-advisory-reconciliation.md) — reconcile advisory findings with gates
- [ADR-0008](adr/0008-sister-response-contract.md) — sister-agent ux-response contract
- [ADR-0009](adr/0009-rust-mermaid-renderer-evaluation.md) — mmdr evaluation (not adopted)
- [ADR-0010](adr/0010-bold-proposals-and-opportunity-coverage.md) — bold proposals and ODI served classes
- [ADR-0011](adr/0011-stage-job-linkage-and-coverage-gate.md) — stage→job linkage and the coverage gate
- [ADR-0012](adr/0012-intake-touchpoint-candidates.md) — intake-image touchpoint candidates
- [ADR-0013](adr/0013-service-blueprint-and-emotion-curve-projections.md) — blueprint swimlane + CJM emotion projections
- [ADR-0014](adr/0014-hig-numeric-gates-and-structural-projections.md) — HIG numeric gates + mindmap/sequence/WBS
- [ADR-0015](adr/0015-producer-cmf-and-interaction-content.md) — producer plan, CMF, interaction content with bard cues
- [ADR-0016](adr/0016-png-renders-and-inline-images.md) — PNG renders and inline image observations
- [ADR-0017](adr/0017-development-coverage-gate.md) — development-only coverage gate
- [ADR-0018](adr/0018-attest-published-tools-images.md) — attest published tools images
- [ADR-0019](adr/0019-hash-bound-slp-v2-and-liaison-gates.md) — hash-bound SLP v2 and deterministic liaison reconciliation
- [ADR-0020](adr/0020-structural-coverage.md) — structural coverage gate (C0, C1, C2, MC/DC, boundaries)
