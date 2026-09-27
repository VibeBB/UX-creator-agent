# UX-creator-agent

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/VibeBB/UX-creator-agent)

**VibeBB UX-creator-agent** is an
[OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk)
plugin that turns a product idea into an auditable **UX contract** —
personas, Jobs-to-be-Done with ODI opportunity scores, customer journeys,
service blueprints, statecharts, feedback budgets, experience loops, and a
QCD stance — and projects it into diagrams (Mermaid, PlantUML, XState v5,
SCXML, Storybook story requirements) with deterministic gates, sha256
provenance, and a design report.

It is the UX design member of the VibeBB sister-plugin family
(`wire-agent`, `mechanical-agent`, `electrical-circuit-agent`,
`bard-agent`).

- **Target**: OpenHands Software Agent SDK **v1.49.6**, Python 3.12+
- **Contract**: `{product}.ux.json` (`schema_version: 1`,
  `system: "ux-creator"`) — personas, jobs (ODI), journeys (typed
  stages with job links), service blueprint, statecharts
  (guards/actions/entry/exit),
  `feedback[]` (Nielsen-budgeted trigger→response), `loops[]`
  (action→reward cadence), QCD, imports — see
  `src/ux_creator/contract.py`
- **Design expression**: idiomatic Ruby via `ruby/lib/ux_dsl.rb` —
  `python -m ux_creator from-ruby design.rb`
- **Plugin**: `plugins/ux` — agents `ux-creator`, `ux-research`,
  `ux-statechart`, `ux-review`, `ux-liaison`; commands `doctor`,
  `discover`, `journey`, `statechart`, `review`, `propose`; skills for
  workflow, persona, theory lenses, JTBD, diagrams, Ruby style, and
  sister cooperation
- **Tools image**: `ghcr.io/vibebb/ux-tools` — Ruby 4, Semeru OpenJ9 JRE,
  PlantUML MIT, mermaid-cli + Chromium, mruby, graphviz, rubocop/minitest
- **Docs**: `docs/README.md` — operations guide, ADRs, research notes

## Layout

```text
src/ux_creator/      # deterministic UX core
├── contract.py      # UXContract schema — the truth source
├── gates.py         # authoritative fail-closed gate runner
├── projections.py   # mmd/puml/xstate/scxml/blueprint/emotion/mindmap/
│                          sequence/wbs/stories/odi/manifest/provenance
├── render.py        # mmdc + plantuml subprocess rendering
├── imports.py       # sister contract import adapters (copy-in + sha256)
├── requests.py      # ux-request.json writers (low/high risk)
├── proposals.py     # QCD triage: .ux-proposals.json → triage + auto ux-requests
├── responses.py     # sister ux-response.json reconciliation (liaison)
├── advisory.py      # typed L2 visual-review records (never verdicts)
├── report.py        # ux-report.json/.md
├── doctor.py        # environment probe
├── ruby_bridge.py   # ruby/mrbc subprocess adapters
├── cli.py           # python -m ux_creator {doctor,gates,author,render,
│                    #   import,from-ruby,mruby-check,request,propose,review-record,review-reconcile,
│                    #   liaison}
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

# Author from the committed contract (inside the locked ux-tools image)
uv run python scripts/run_in_locked_image.py -- \
  python scripts/e2e_authoring.py \
  --contract examples/smart-kettle/smart-kettle.ux.json \
  --out out/smart-kettle --render

# Or express it in Ruby
ruby ruby/bin/ux-dsl examples/smart-kettle/smart-kettle.ux.rb
```

All UX tool execution runs inside the locked `ux-tools` image; the host
needs only uv, Python 3.12, git, and Docker. Set `UX_TOOLS_IMAGE` to run
against a locally built image instead of the published digest lock.

## Sister cooperation

ux-creator imports circuit connectivity (`system:"circuit"`), mech
envelopes (`"mech"`), wire harness contracts (`"wire"`), and bard
artifacts as **touchpoint candidates** — copied in with sha256
provenance, recorded in `imports[]`. It sends change proposals to
sister agents via `<name>.ux-request.json`: low-risk requests are
deliverable; high-risk requests must cite a job id in the rationale.
`ux propose` triages a `*.ux-proposals.json` batch deterministically —
layer-based risk decides auto-send vs hold. See ADR-0003 and ADR-0006.

## Safety model

- Gates (`gates.py`) are the only verdict source — statechart
  reachability/initial/events/dead-ends/determinism, journey surface
  references, emotion≤2 ⇒ pain point, JTBD three-dimension, non-empty
  `core_experience`, import sha256, feedback surface/trigger/latency
  budgets, loop step/closure, onboarding presence. `unknown` never
  passes.
  `hig.*` adds target-size (≥7.8 mm) and WCAG contrast checks on
  declared `controls:`.
- `protect_generated` + `safety_rail` hooks deny hand edits to generated
  projections and dangerous writes.
- Vision observations are L2 advisory records (`*.ux-vision.jsonl`,
  `review-visual-*.advisory.json`) — they steer, never verdict.

## License

BSD 3-Clause © VibeBB. Bundled third-party components are listed in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

---

## 日本語セクション（Japanese）

**VibeBB UX-creator-agent** は、プロダクトのアイデアを監査可能な
**UX コントラクト**（ペルソナ、JTBD と ODI 機会スコア、カスタマージャーニー、
サービスブループリント、ステートチャート、フィードバック予算、
体験ループ、QCD 方針）に変換する
[OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk)
プラグインです。コントラクトは Mermaid / PlantUML / XState v5 / SCXML /
Storybook ストーリー要件に投影され、決定論的ゲート・sha256 プロベナンス・
デザインレポートを出力します。

VibeBB 姉妹プラグインファミリー（`wire-agent`、`mechanical-agent`、
`electrical-circuit-agent`、`bard-agent`）の UX デザイン担当です。

- **対象**: OpenHands Software Agent SDK **v1.49.6**、Python 3.12+
- **コントラクト**: `{product}.ux.json`（`schema_version: 1`、
  `system: "ux-creator"`）— ペルソナ、ジョブ（ODI）、ジャーニー（種別付き
  ステージ）、サービスブループリント、ステートチャート
  （guard/actions/entry/exit）、`feedback[]`（Nielsen 予算付き
  トリガー→応答）、`loops[]`（行動→報酬のケイデンス）、QCD、インポート —
  `src/ux_creator/contract.py` を参照
- **デザイン記述**: イディオマティックな Ruby DSL `ruby/lib/ux_dsl.rb` —
  `python -m ux_creator from-ruby design.rb`
- **プラグイン**: `plugins/ux` — エージェント `ux-creator`、`ux-research`、
  `ux-statechart`、`ux-review`、`ux-liaison`；コマンド `doctor`、
  `discover`、`journey`、`statechart`、`review`、`propose`；ワークフロー、
  ペルソナ、理論レンズ、JTBD、ダイアグラム、Ruby スタイル、姉妹連携の
  スキル
- **ツールイメージ**: `ghcr.io/vibebb/ux-tools` — Ruby 4、Semeru OpenJ9
  JRE、PlantUML MIT、mermaid-cli + Chromium、mruby、graphviz、
  rubocop/minitest
- **ドキュメント**: `docs/README.md` — 運用ガイド、ADR、リサーチノート

### レイアウト

構成は英語セクションの「Layout」と同一です（`src/ux_creator/` が決定論
コア、`plugins/ux/` が OpenHands プラグイン、`ruby/` が DSL、`docker/` が
ツールイメージ、`examples/` がスマートケトルの例、`scripts/`・`tests/`・
`docs/` が検証・テスト・文書）。

### クイックスタート

```bash
uv sync
uv run python scripts/verify_all.py --stage fast

# コミット済みコントラクトから生成（ロックされた ux-tools イメージ内で実行）
uv run python scripts/run_in_locked_image.py -- \
  python scripts/e2e_authoring.py \
  --contract examples/smart-kettle/smart-kettle.ux.json \
  --out out/smart-kettle --render

# あるいは Ruby で記述する
ruby ruby/bin/ux-dsl examples/smart-kettle/smart-kettle.ux.rb
```

UX ツールはすべてロックされた `ux-tools` イメージ内で実行されます。ホスト
に必要なのは uv、Python 3.12、git、Docker のみです。公開済みダイジェスト
ロックの代わりにローカルビルドのイメージを使う場合は `UX_TOOLS_IMAGE`
を設定します。

### 姉妹連携

ux-creator は回路の接続情報（`system:"circuit"`）、メカの外形
（`"mech"`）、ワイヤーハーネスのコントラクト（`"wire"`）、bard の成果物を
**タッチポイント候補**としてインポートします — sha256 プロベナンス付きで
コピーインし、`imports[]` に記録します。姉妹エージェントへの変更提案は
`<name>.ux-request.json` で送ります: 低リスクの要求はそのまま送付可能、
高リスクの要求は根拠に job id の引用が必須です。`ux propose` は
`*.ux-proposals.json` のバッチを決定論的にトリアージし、レイヤー由来の
リスクで自動送付か保留かを決めます。ADR-0003 と ADR-0006 を参照。

### 安全モデル

- ゲート（`gates.py`）が唯一の判定源です — ステートチャートの
  到達性/初期状態/イベント/行き止まり/決定性、ジャーニーのサーフェス参照、
  emotion≤2 ⇒ ペインポイント必須、JTBD 三次元、空でない
  `core_experience`、インポートの sha256、フィードバックのサーフェス/
  トリガー/レイテンシ予算、ループのステップ/閉包、オンボーディングの存在。
  `unknown` は決して pass になりません。
- `protect_generated` と `safety_rail` フックが生成物の手編集と危険な
  書き込みを拒否します。
- Vision の観察は L2 アドバイザリ記録（`*.ux-vision.jsonl`、
  `review-visual-*.advisory.json`）です — 判断を導きますが、判定はしません。

### ライセンス

BSD 3-Clause © VibeBB。同梱するサードパーティコンポーネントは
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) に記載しています。
