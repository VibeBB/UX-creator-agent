# Commands

The deterministic CLI is `python -m ux_creator`. The OpenHands plugin also
provides slash commands. For tools that write files, use a workspace copy and
review the diff; `protect-generated` blocks direct edits to generated output.

## CLI subcommands

| Subcommand | Inputs and effect |
| --- | --- |
| `doctor` | Probe Ruby, mruby, Mermaid, PlantUML, and plugin image availability; `--warn` is a non-blocking session-start probe. |
| `gates` | Read a contract and report deterministic checks; optional `--out` writes a report and `--workspace` sets the path boundary. |
| `author` | Read a contract, run gates, write projections/report to required `--out`; optional `--render` produces previews. |
| `render` | Render top-level `*.mmd` and `*.puml` files in a directory. |
| `import` | Read a supported `circuit`, `mech`, `wire`, `bard`, or `csv` input and update contract import provenance. |
| `from-ruby` | Compile a Ruby DSL source to the required `--out` contract JSON. |
| `mruby-check` | Syntax-check a Ruby source with `mrbc -c`. |
| `request` | Write a v2 request; repeat `--change`, `--input`, `--deliverable`, `--accept`, and optional `--depends-on`. High-risk requests need a declared job ID in `--rationale`; `--replace` is required to replace a different existing request. |
| `delegate` | Read a request and print its deterministic task-tool brief. |
| `propose` | Read a contract and proposal set, write triage and eligible requests to `--out-dir`. |
| `review-record` | Write an image-bound advisory review with checklist, summary, and repeatable `--finding CATEGORY:SEVERITY:WHERE:OBSERVATION`; use `--not-applicable` if a vision-capable review could not be performed. |
| `review-reconcile` | Compare review advisories in `--out-dir` with contract and gate truth; findings remain advisory. |
| `liaison` | Reconcile requests and responses under `--liaison-dir` (default workspace liaison directory). |
| `produce` | Validate a product plan and write status under required `--out`; `--workspace`, `--liaison-dir`, and `--render` are optional. |
| `intake-record` | Record image touchpoint candidates with repeatable `--touchpoint ID[@SURFACE]=EVIDENCE`. |
| `intake-reconcile` | Compare intake advisory records in `--out-dir` with contract-declared touchpoints. |
| `record` | Append `decision`, `impression`, or `vision-review` from a JSON payload; `record status` summarizes VRP logs. |

The CLI serializes handled failures as a JSON result with `verdict: fail`,
`stage`, `detail`, and `error_type`. Unknown inputs and missing required
arguments are rejected by argparse or the strict model validators.

Examples:

```bash
uv run python -m ux_creator gates examples/smart-kettle/smart-kettle.ux.json
uv run python -m ux_creator author examples/smart-kettle/smart-kettle.ux.json \
  --out out/smart-kettle --render
uv run python -m ux_creator liaison --workspace examples/smart-kettle
uv run python -m ux_creator produce examples/smart-kettle-product/smart-kettle.production.json \
  --workspace examples/smart-kettle-product --liaison-dir examples/smart-kettle-product/requests \
  --out out/production
```

## OpenHands slash commands

| Command | Purpose |
| --- | --- |
| `cmf` (`/ux:cmf`) | Edit and validate the authored contract's CMF block. |
| `content` (`/ux:content`) | Map feedback to interaction assets and coordinate bard cues. |
| `discover` (`/ux:discover`) | Reframe requirements into personas, JTBD/ODI jobs, and journeys. |
| `doctor` (`/ux:doctor`) | Diagnose the UX tool environment. |
| `journey` (`/ux:journey`) | Author journeys and service blueprints. |
| `produce` (`/ux:produce`) | Coordinate product-level work through `ux-producer`. |
| `propose` (`/ux:propose`) | QCD-triage proposals into sister requests. |
| `review` (`/ux:review`) | Delegate advisory review of rendered artifacts. |
| `statechart` (`/ux:statechart`) | Author statecharts and their projections. |

Slash command descriptions and allowed tools are defined in
`plugins/ux/commands/`. The CLI and MCP surfaces are documented separately in
[MCP](mcp.md).
