# UX-creator-agent

**VibeBB UX-creator-agent** is an
[OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk)
plugin that turns a product idea into an auditable **UX contract** —
personas, Jobs-to-be-Done with ODI opportunity scores, customer journeys,
service blueprints, statecharts, and a QCD stance — and projects it into
diagrams (Mermaid, PlantUML, XState v5, SCXML, Storybook story
requirements) with deterministic gates, sha256 provenance, and a design
report.

It is the UX design sibling in the VibeBB plugin family
(`wire-agent`, `mechanical-agent`, `electrical-circuit-agent`,
`bard-agent`). The designer persona speaks Japanese (Hakata dialect) in
thinking and Japanese conversation, Southern (Virginia) American English
in English — see the `ux-persona` skill.

- **Target**: OpenHands Software Agent SDK **v1.49.6**, Python 3.12+
- **Contract**: `{product}.ux.json` (`schema_version: 1`,
  `system: "ux-creator"`) — see `src/ux_creator/contract.py`
- **Design expression**: idiomatic Ruby via `ruby/lib/ux_dsl.rb` —
  `python -m ux_creator from-ruby design.rb`
- **Plugin**: `plugins/ux` — agents `ux-creator`, `ux-research`,
  `ux-statechart`, `ux-review`, `ux-liaison`; commands `doctor`,
  `discover`, `journey`, `statechart`, `review`, `propose`; skills for
  workflow, persona, theory lenses, JTBD, diagrams, Ruby style, and
  sibling cooperation
- **Tools image**: `ghcr.io/vibebb/ux-tools` — Ruby 4, Semeru OpenJ9 JRE,
  PlantUML MIT, mermaid-cli + Chromium, mruby, graphviz, rubocop/minitest
- **Docs**: `docs/README.md` — operations guide, ADRs, research notes

## Layout

```text
src/ux_creator/      # deterministic UX core
├── contract.py      # UXContract schema — the truth source
├── gates.py         # authoritative fail-closed gate runner
├── projections.py   # mmd/puml/xstate/scxml/stories/odi/manifest/provenance
├── render.py        # mmdc + plantuml subprocess rendering
├── imports.py       # sibling contract import adapters (copy-in + sha256)
├── requests.py      # ux-request.json writers (low/high risk)
├── advisory.py      # typed L2 visual-review records (never verdicts)
├── report.py        # ux-report.json/.md
├── doctor.py        # environment probe
├── ruby_bridge.py   # ruby/mrbc subprocess adapters
├── cli.py           # python -m ux_creator {doctor,gates,author,render,
│                    #   import,from-ruby,mruby-check,request,review-record}
└── mcp_server.py    # stdio MCP boundary (deterministic tools only)
plugins/ux/          # OpenHands plugin (agents/commands/skills/hooks/launcher)
ruby/                # ux-dsl library, bin/ux-dsl, .rubocop.yml, minitest
docker/              # ux-tools.Dockerfile + puppeteer-config.json
examples/            # smart-kettle (.ux.rb source + generated .ux.json)
scripts/             # verify_all, check_plugin_load, locked-image helpers,
                     # e2e_authoring, check_ruby_dsl, release tooling
tests/               # pytest suite incl. negative gate tests
docs/                # operations.md, adr/, research/
```

## Quick start

```bash
uv sync
uv run python scripts/verify_all.py --stage fast

# Author from the committed contract
UX_TOOLS_IMAGE=<locked-image> uv run python scripts/run_in_locked_image.py -- \
  python scripts/e2e_authoring.py \
  --contract examples/smart-kettle/smart-kettle.ux.json \
  --out out/smart-kettle --render

# Or express it in Ruby
ruby ruby/bin/ux-dsl examples/smart-kettle/smart-kettle.ux.rb
```

All UX tool execution runs inside the locked `ux-tools` image; the host
needs only uv, Python 3.12, git, and Docker.

## Sibling cooperation

ux-creator imports circuit connectivity (`system:"circuit"`), mech
envelopes (`"mech"`), wire harness contracts (`"wire"`), and bard
artifacts as **touchpoint candidates** — copied in with sha256
provenance, recorded in `imports[]`. It sends change proposals to
siblings via `<name>.ux-request.json`: low-risk requests are deliverable;
high-risk requests must cite a job id in the rationale. See ADR-0003.

## Safety model

- Gates (`gates.py`) are the only verdict source — statechart
  reachability/initial/events/dead-ends, journey surface references,
  emotion≤2 ⇒ pain point, JTBD three-dimension, non-empty
  `core_experience`, import sha256. `unknown` never passes.
- `protect_generated` + `safety_rail` hooks deny hand edits to generated
  projections and dangerous writes.
- Vision observations are L2 advisory records (`*.ux-vision.jsonl`) —
  they steer, never verdict.

## License

BSD 3-Clause © VibeBB. Bundled third-party components are listed in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

---

## 日本語セクション（Japanese）

**UX-creator-agent** は、プロダクトのアイデアを監査可能な **UX コントラクト**
（ペルソナ、JTBD+ODI スコア、カスタマージャーニー、サービスブループリント、
ステートチャート、QCD 方針）に変換する OpenHands プラグインです。
コントラクトは Mermaid / PlantUML / XState / SCXML / Storybook に投影され、
決定論的ゲートと sha256 プロベナンス付きのデザインレポートを出力します。

- 契約ファイル: `{product}.ux.json`（`schema_version: 1`,
  `system: "ux-creator"`）
- デザイン記述: イディオマティックな Ruby DSL（`ruby/lib/ux_dsl.rb`）
- 実行環境: `ghcr.io/vibebb/ux-tools` コンテナ内で全ツールを実行
- 兄弟プラグイン連携: circuit/mech/wire/bard の成果物を sha256 付きで
  インポートし、`ux-request.json` で変更提案を返送（高リスクは job id の
  引用が必須）
- 設計者ペルソナ: 日本語では博多弁、英語ではバージニア南部英語 —
  `plugins/ux/skills/ux-persona` を参照

ライセンスは BSD 3-Clause © VibeBB です。
