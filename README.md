# UX-creator-agent

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/VibeBB/UX-creator-agent)

VibeBB UX-creator-agent helps a product team turn an idea into a reviewable,
testable user experience. It is an OpenHands plugin: describe the product and
its users in conversation, and the UX agents help shape the work into a UX
contract, diagrams, checks, and clear questions for the rest of the product
team.

## What you can do with it

- Describe a product idea, its users, constraints, and what success should
  feel like.
- Explore functional, emotional, and social user needs before choosing a
  feature or interface.
- Map journeys, service touchpoints, feedback, product states, and interaction
  content.
- Ask a specialist UX agent to author CMF guidance, statecharts, visual
  reviews, or a product-level plan.
- Record why a choice was made, what evidence informed it, what happened at a
  project stage, and what a vision review observed.
- Coordinate requests with VibeBB sister teams and see whether each request is
  open, answered, stale, blocked, or needs attention.

The plugin checks declared design rules consistently. A successful check is
evidence that the declared rules passed; it is not a guarantee that a product
is safe, accessible, manufacturable, or right for every user. Human review and
domain specialists remain essential.

## How to start in AgentCanvas or OpenHands

1. Open a project workspace in an AgentCanvas or OpenHands environment where
   the VibeBB `ux` plugin is installed.
2. Make sure that environment has Docker available and can access the
   digest-pinned `ux-tools` image. The plugin does not silently substitute an
   unpinned local image.
3. Start with the `ux-creator` agent and describe the product, intended users,
   constraints, and the decision you need help making. Attach existing
   contracts, diagrams, or images when they are relevant.
4. Review the questions and generated contract with the team. Ask for
   specialist help when useful: `ux-research`, `ux-statechart`, `ux-review`,
   `ux-liaison`, or `ux-producer`.
5. Resolve failed or unknown checks before treating a design as ready. Record
   important decisions and completed-stage impressions in the workspace.

No command-line setup is needed to begin a conversation when the host
environment is already configured. Developers setting up a checkout should
use [Development](docs/development.md).

## What the team receives

The authored `{product}.ux.json` contract captures personas, Jobs-to-be-Done
and ODI opportunity scores, journeys, service blueprints, statecharts,
feedback, experience loops, product surfaces, CMF, and interaction content.
From that source of truth, the plugin can create:

- Journey, statechart, service-blueprint, emotion, sequence, work-breakdown,
  and mind-map diagrams.
- XState v5 and SCXML state-machine exports, wireframe source, Storybook
  requirements, CMF and content maps, and ODI tables.
- A machine-readable and human-readable UX report, deterministic gate
  results, and SHA-256 provenance.
- Hash-bound sister requests and reconciled responses, plus production-plan
  status and next actions.
- Append-only decision, stage-impression, and vision-review evidence.

Generated files are projections. The authored contract and project evidence
remain the sources of truth; generated files should be regenerated rather than
edited by hand.

## Working with the VibeBB family

UX-creator-agent is one of eleven repositories in the family. The UX liaison
registry recognizes these ten sister targets:

| Target | Sister repository | Typical contribution |
| --- | --- | --- |
| `bard` | `bard-agent` | Sound cues and music |
| `circuit` | `electrical-circuit-agent` | Electrical design |
| `dashboard` | `dashboard-agent` | Operator and telemetry interfaces |
| `doc` | `document-agent` | User and maintainer documentation |
| `firmware` | `firmware-agent` | Embedded software |
| `fpga` | `fpga-agent` | Programmable logic |
| `mech` | `mechanical-agent` | Enclosure and mechanical design |
| `prodeng` | `production-engineering-agent` | Manufacturing and production engineering |
| `sim` | `simulation-agent` | Simulation and analysis |
| `wire` | `wire-agent` | Electrical wiring and harnesses |

Requests and responses are workspace files with normalized paths and SHA-256
evidence. The UX agent can prepare a deterministic task brief for a sister
agent, but a request is not complete until a valid response and its evidence
have been reconciled. Read [Sister cooperation](docs/sister-cooperation.md)
for the exchange format and [Records and vision](docs/records-and-vision.md)
for the evidence trail.

## Important boundaries

- The plugin is advisory and authoring support; it does not replace user
  research, accessibility testing, legal review, engineering sign-off, or
  manufacturing validation.
- Deterministic gates judge only fields and evidence that the contract
  declares. Missing tools or insufficient evidence remain `unknown` and do
  not become a pass.
- Vision reviews and impressions are advisory. They can identify concerns,
  but they cannot override deterministic gate results.
- Sister cooperation is explicit. This repository defines the UX-side
  registry and protocol; each sister repository owns its own inbox and
  response implementation.
- The plugin runs its authoring and rendering tools inside the pinned
  `ux-tools` Docker image. Docker and access to that image are required for
  those operations.

## Documentation

- [Architecture](docs/architecture.md) and [workflow](docs/workflow.md)
- [Agents](docs/agents.md), [skills](docs/skills.md), and
  [commands](docs/commands.md)
- [MCP tools](docs/mcp.md), [hooks](docs/hooks.md), and
  [contract formats](docs/contracts.md)
- [Sister cooperation](docs/sister-cooperation.md) and
  [records and vision](docs/records-and-vision.md)
- [Performance and limits](docs/performance-and-limits.md),
  [operations](docs/operations.md), and
  [development](docs/development.md)
- [Improvement notes](docs/improvement-notes.md) and the
  [documentation index](docs/README.md)

The project is BSD 3-Clause licensed. Third-party component notices are in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## 日本語

VibeBB UX-creator-agent は、製品のアイデアをレビュー・検証できるユーザー
体験へ整理する OpenHands プラグインです。AgentCanvas または OpenHands の
会話で製品と利用者について説明すると、UX エージェントが UX コントラクト、
図、チェック結果、製品チームへの質問をまとめます。

### できること

- 製品のアイデア、利用者、制約、成功したときの体験を説明する。
- 機能や画面を決める前に、利用者の機能的・感情的・社会的なニーズを整理する。
- ジャーニー、サービスの接点、フィードバック、製品の状態、操作コンテンツを
  モデル化する。
- CMF、ステートチャート、ビジュアルレビュー、製品全体の計画を専門 UX
  エージェントに依頼する。
- 選択の理由、根拠、各段階での所感、ビジョンレビューの観察を記録する。
- VibeBB の姉妹チームに依頼し、未回答・回答済み・古い・ブロック中などの
  状態を確認する。

プラグインは、宣言された設計ルールを一貫して確認します。チェック成功は
宣言されたルールが通過したという根拠であり、製品が安全、アクセシブル、
製造可能、あるいはすべての利用者に適切であることを保証するものではありま
せん。人によるレビューと専門家の判断が引き続き必要です。

### AgentCanvas または OpenHands で始める

1. VibeBB の `ux` プラグインがインストールされた AgentCanvas または
   OpenHands のプロジェクトワークスペースを開きます。
2. 環境から Docker を利用でき、ダイジェスト固定された `ux-tools` イメージに
   アクセスできることを確認します。固定されていないローカルイメージへ暗黙に
   切り替えることはありません。
3. `ux-creator` エージェントを開始し、製品、対象利用者、制約、判断したい内容を
   説明します。関連する既存コントラクト、図、画像も添付できます。
4. 質問と生成されたコントラクトをチームで確認します。必要に応じて
   `ux-research`、`ux-statechart`、`ux-review`、`ux-liaison`、`ux-producer`
   に専門作業を依頼します。
5. デザインを完成扱いにする前に、失敗または unknown のチェックを解決します。
   重要な判断と完了した段階の所感をワークスペースに記録します。

ホスト環境が設定済みなら、会話を始めるためのコマンドライン設定は不要です。
リポジトリを開発者として準備する場合は
[開発ガイド](docs/development.md)を参照してください。

### チームが受け取るもの

作成する `{product}.ux.json` コントラクトには、ペルソナ、Jobs-to-be-Done と
ODI 機会スコア、ジャーニー、サービスブループリント、ステートチャート、
フィードバック、体験ループ、製品サーフェス、CMF、操作コンテンツが含まれます。
この情報をもとに、次の成果物を生成できます。

- ジャーニー、ステートチャート、サービスブループリント、感情曲線、シーケンス、
  作業分解、マインドマップの図。
- XState v5 / SCXML の状態機械、ワイヤーフレームのソース、Storybook の要件、
  CMF / コンテンツマップ、ODI テーブル。
- 機械可読・人間可読な UX レポート、決定論的なゲート結果、SHA-256
  プロベナンス。
- ハッシュで根拠を結び付けた姉妹チームへの依頼と回答、製品計画の状態と次の作業。
- 追記専用の判断、段階所感、ビジョンレビュー記録。

生成ファイルはコントラクトから作られる投影です。作成済みファイルを手編集せず、
コントラクトとプロジェクトの根拠を情報源として再生成してください。

### VibeBB ファミリーとの連携

UX-creator-agent はファミリー内の 11 リポジトリの一つです。UX のレジストリは
次の 10 姉妹ターゲットを認識します。

| ターゲット | 姉妹リポジトリ | 主な担当 |
| --- | --- | --- |
| `bard` | `bard-agent` | サウンドキューと音楽 |
| `circuit` | `electrical-circuit-agent` | 電気設計 |
| `dashboard` | `dashboard-agent` | オペレーター・テレメトリ UI |
| `doc` | `document-agent` | 利用者・保守者向けドキュメント |
| `firmware` | `firmware-agent` | 組み込みソフトウェア |
| `fpga` | `fpga-agent` | プログラマブルロジック |
| `mech` | `mechanical-agent` | 外装・機械設計 |
| `prodeng` | `production-engineering-agent` | 製造・生産技術 |
| `sim` | `simulation-agent` | シミュレーション・解析 |
| `wire` | `wire-agent` | 電気配線・ハーネス |

依頼と回答は、正規化されたパスと SHA-256 根拠を含むワークスペースファイル
です。UX エージェントは決定論的なタスク依頼を準備できますが、有効な回答と
根拠を照合するまでは完了になりません。
[姉妹連携](docs/sister-cooperation.md)と
[記録・ビジョン](docs/records-and-vision.md)を参照してください。

### 大切な制約

- このプラグインは UX 作成を支援しますが、ユーザー調査、アクセシビリティ検証、
  法務レビュー、エンジニアリング承認、製造検証の代わりにはなりません。
- 決定論的ゲートが判定するのは、コントラクトで宣言された項目と根拠だけです。
  ツールや根拠が不足する場合は `unknown` となり、pass にはなりません。
- ビジョンレビューと所感は助言です。懸念を指摘できますが、決定論的ゲートの
  結果を上書きできません。
- 姉妹連携は明示的に行います。このリポジトリが定義するのは UX 側のレジストリと
  プロトコルであり、受信・回答処理は各姉妹リポジトリが所有します。
- 作成・描画ツールは固定された `ux-tools` Docker イメージ内で実行されます。
  これらの操作には Docker とイメージへのアクセスが必要です。

### ドキュメント

- [アーキテクチャ](docs/architecture.md)と[ワークフロー](docs/workflow.md)
- [エージェント](docs/agents.md)、[スキル](docs/skills.md)、
  [コマンド](docs/commands.md)
- [MCP ツール](docs/mcp.md)、[フック](docs/hooks.md)、
  [コントラクト形式](docs/contracts.md)
- [姉妹連携](docs/sister-cooperation.md)と[記録・ビジョン](docs/records-and-vision.md)
- [性能と制限](docs/performance-and-limits.md)、
  [運用](docs/operations.md)、[開発](docs/development.md)
- [改善ノート](docs/improvement-notes.md)と
  [ドキュメント索引](docs/README.md)

本プロジェクトは BSD 3-Clause ライセンスです。第三者コンポーネントの通知は
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) にあります。
