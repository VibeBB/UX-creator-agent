# docker/

- `ux-tools.Dockerfile` — the deterministic UX tool execution image:
  ruby:4.0.7-slim-trixie base, uv 0.12.23 → CPython 3.14 venv at
  `/opt/ux/.venv`, IBM Semeru OpenJ9 JRE 27 (`/opt/jre`), PlantUML MIT jar
  (`/opt/plantuml/plantuml.jar`, `PLANTUML_JAR`), mruby 4.0.0
  (`/opt/mruby/bin`), Node.js 26 (sha256-pinned `nodejs.org` tarball →
  `/usr/local`, npm vendored deps patched for publish-gate CVEs) +
  `@mermaid-js/mermaid-cli` 12 + Debian
  Chromium (puppeteer via `docker/puppeteer-config.json`,
  `--no-sandbox`), Graphviz, CJK fonts, rubocop + minitest, non-root
  `ux` (uid 1000). Build-time smoke: doctor, Ruby DSL → contract →
  author → gates pass, `mrbc -c`, `mmdc` render, `plantuml -testdot`,
  rubocop.
- `image-digests.json` — the image digest lock, written only by
  `publish-ux-images.yml`; never commit placeholder entries. Until the
  first publish, `$UX_TOOLS_IMAGE` selects the image.

Build locally:

```bash
docker build -f docker/ux-tools.Dockerfile -t ux-tools:dev .
UX_TOOLS_IMAGE=ux-tools:dev uv run python scripts/run_in_locked_image.py -- \
  python scripts/e2e_authoring.py \
  --contract examples/smart-kettle/smart-kettle.ux.json \
  --out out/smart-kettle --render
```
