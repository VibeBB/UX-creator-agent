# ADR-0004: PlantUML MIT jar and tool license policy

- Status: Accepted
- Date: 2026-09-26

## Context

The default PlantUML jar is GPL-licensed; the repo invariant forbids
import-binding GPL/AGPL/LGPL code (copyleft tools may only run as
unmodified subprocesses). Maven Central also rate-limits CI fetches.

## Decision

Ship the **`plantuml-mit` jar** (MIT license) fetched from GitHub
releases with a sha256 check, at `/opt/plantuml/plantuml.jar`
(`PLANTUML_JAR`). The MIT build lacks Ditaa/Sudoku support, which the UX
projections (state diagrams, Salt wireframes) do not use.

Tool license summary (all run as subprocesses or npm/gem installs, never
import-linked): Mermaid + mermaid-cli (MIT), Chromium (BSD), Graphviz
(EPL-1.0), Semeru OpenJ9 (GPLv2+Classpath Exception / EPL-2.0 /
Apache-2.0 — JRE only, no linking), mruby (MIT), Ruby (Ruby/BSD-2),
rubocop + minitest (MIT), Node.js (MIT).

Not adopted: Figma/Overflow (proprietary SaaS — ux-creator emits
`.stories.json`/XState requirements instead); Penpot (server product);
GPL PlantUML jar; maven-central plantuml artifacts.

## Consequences

`THIRD_PARTY_NOTICES.md` lists every component; `scripts/
check_dependency_updates.py` tracks the ARG pins (`SEMERU_JRE_VERSION`,
`PLANTUML_VERSION`, `MRUBY_VERSION`, `MERMAID_CLI_VERSION`, `UV_VERSION`,
`RUBOCOP_VERSION`, `MINITEST_VERSION`).
