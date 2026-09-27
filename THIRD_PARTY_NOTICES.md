# Third-Party Notices

`UX-creator-agent` is licensed under the BSD 3-Clause License (see
`LICENSE`). The `ux-tools` container image and development environment
bundle or invoke the third-party components below. All of them are used
as unmodified subprocesses or package-manager installs — none is
import-linked into `ux_creator` (per ADR-0004).

| Component | Version pin | License | Notes |
|---|---|---|---|
| Ruby | `ruby:4.0.7-slim-trixie` (digest-pinned) | Ruby License / BSD-2-Clause | Base image; DSL runtime |
| Debian 13 (trixie) packages | apt `graphviz`, `chromium`, `nodejs`, `npm`, `fonts-ipafont`, `fonts-noto-cjk`, `build-essential`, `bison`, `git`, `curl`, `ca-certificates`, `xz-utils` | various (GPL-family system tools, BSD, OFL, IPA Font License) | OS layer only |
| uv | `ghcr.io/astral-sh/uv:0.12.19` | Apache-2.0 / MIT | Python + package manager |
| CPython | 3.12.x via `uv python install` | PSF-2.0 | Agent runtime |
| IBM Semeru OpenJ9 JRE | `27.0.0.0` sha256-pinned tarball → `/opt/jre` | GPLv2 + Classpath Exception, EPL-2.0, Apache-2.0 (per component; see `license/` inside the JRE) | PlantUML runtime only — no linking |
| PlantUML MIT jar | `v1.2026.8` sha256-pinned → `/opt/plantuml/plantuml.jar` | MIT | Diagram renderer (subprocess) |
| Graphviz | Debian package | EPL-1.0 | PlantUML layout engine (`dot`) |
| Mermaid + mermaid-cli | `@mermaid-js/mermaid-cli@12.0.0` | MIT | Journey/statechart render (`mmdc`) |
| Chromium | Debian package | BSD-3-Clause | Puppeteer headless browser (`--no-sandbox` config committed) |
| Node.js | Debian package (LTS) | MIT | mermaid-cli runtime |
| mruby | `4.0.0` sha256-pinned tarball → `/opt/mruby` | MIT | `mruby`/`mrbc` for firmware-side UX checks |
| rubocop | `gem rubocop:1.91.0` | MIT | Ruby linter |
| minitest | `gem minitest:6.0.6` | MIT | Ruby test framework |
| pydantic | `>=2` via `uv.lock` | MIT | Contract models |
| mcp | `>=1.29,<2` via `uv.lock` | MIT | MCP server SDK |
| openhands-sdk / openhands-tools | `1.49.6` (sdk-check group) | MIT | CI plugin-load verification only |
| fonts-ipafont / fonts-noto-cjk | Debian packages | IPA Font License / SIL OFL-1.1 | CJK glyphs in rendered SVG/PNG |

## Sources recorded in the image

The Dockerfile writes `SOURCE` files under `/usr/share/doc/` for each
manual install (semeru-jre, plantuml, mruby); apt/npm/gem components
carry their own metadata. Any addition to `docker/ux-tools.Dockerfile`
must add a row here and a license check in the build smoke where
practical.
