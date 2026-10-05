# Architecture

UX-creator-agent turns authored UX models into deterministic checks,
projections, and evidence. The central rule is that the contract and its
workspace-bound evidence are the sources of truth; reports, diagrams, and
status files are generated views.

## Boundaries and data flow

```text
AgentCanvas / OpenHands
  ├─ UX agents and skills
  ├─ stdio MCP tools ─┐
  └─ slash commands ──┴─> ux_launcher.py -> digest-pinned ux-tools container
                                      └─> python -m ux_creator
                                           ├─ validate / deterministic gates
                                           ├─ projections / render / report
                                           ├─ workspace requests / responses
                                           └─ append-only UX evidence
```

- `plugins/ux/` contains agent definitions, commands, skills, lifecycle
  hooks, and the launcher. Prompts describe work; they do not replace
  deterministic validation.
- `src/ux_creator/` is the Python core. CLI and MCP are two interfaces to the
  same models and operations.
- `ruby/` is an optional design-expression DSL. It emits contract JSON which
  the Python model validates; design judgments stay in Python gates.
- `docker/ux-tools.Dockerfile` defines rendering and Ruby tools. Plugin
  execution resolves a pinned image from `UX_TOOLS_IMAGE` or the repository
  lock and does not silently fall back to an unpinned local image.
- The workspace is the collaboration boundary. Paths are resolved beneath
  its root, traversal and symlink escapes are rejected, and exchanged
  artifacts are bound to SHA-256 hashes.

## Execution sequence

1. An agent authors a `{product}.ux.json` contract or compiles `*.ux.rb`.
2. Pydantic models reject extra, malformed, or internally inconsistent
   contract fields.
3. `run_gates` evaluates statecharts, jobs, journeys, feedback, loops,
   imports, opportunity coverage, HIG, CMF, and content.
4. Projection functions derive diagrams and handoff files. Optional render
   subprocesses produce SVG and PNG previews.
5. `write_report` combines deterministic gate results with advisory review,
   intake, liaison, and innovation summaries.
6. Hooks and explicit record tools append decision, stage-impression, and
   vision-review evidence under `observations/ux/`.
7. SLP v2 requests and responses track work across sister targets. The
   product-level plan consumes liaison and evidence state when checking
   production readiness.

`fail` blocks the declared gate. `unknown` means a check could not establish
its result; it is never converted into `pass`. Visual observations are L2
advisory evidence and cannot override the deterministic verdict.

## Core module and function index

These are supported entry points for the Python core. Underscore-prefixed
helpers are private implementation details rather than stable API.

| Module | Public functions and responsibility |
| --- | --- |
| `contract` | `load_contract` validates authored JSON; `contract_sha256` computes canonical contract provenance. |
| `gates` | `run_gates` evaluates the contract; `stage_job_coverage` reports stage/job coverage; `contrast_ratio` computes the HIG color-contrast metric. |
| `projections` | `write_projections` creates contract-derived files; `write_provenance` records hashes for those outputs. |
| `render` | `render_mermaid`, `render_plantuml`, and `render_all` run the pinned external renderers and return per-file statuses. |
| `imports` | `extract_touchpoints` extracts supported candidate references; `import_source` copies supported sister data into contract provenance. |
| `requests` | `build_request` validates and hashes inputs; `write_request` writes without silent replacement; `load_request` validates a request file. |
| `responses` | `liaison_status` reconciles request/response files; `load_response_records` loads valid response records for production checks. |
| `proposals` | `triage` deterministically scores proposals; `write_triage` writes triage and eligible requests. |
| `delegation` | `delegation_brief` creates the stable task-tool payload for a request. |
| `production` | `load_plan`, `plan_sha256`, `run_production_gates`, `stage_rows`, `production_status`, and `write_production` validate plans, gate work, and produce status files. |
| `records` | `record_decision`, `record_impression`, and `record_vision_review` append validated VRP events; `records_summary` reports counts and the latest stop-hook result; `sentence_count` and `impression_is_prose` validate reflections; `sha256_file` and `tree_sha256` bind evidence. |
| `observations` | `collect_records` loads workspace VRP logs; `records_to_dict` serializes the gathered summary. |
| `advisory` | `parse_visual_review`, `write_visual_review`, `write_visual_review_not_applicable`, `load_visual_reviews`, and `reconcile_findings` manage visual review; `normalize_touchpoint`, `parse_intake_record`, `write_intake_record`, `load_intake_records`, and `reconcile_intake` manage image intake. |
| `report` | `review_lens`, `liaison_lens`, and `innovation_lens` build report sections; `build_report`, `write_report`, and `render_markdown` create the final views. |
| `doctor` | `run_doctor` probes the local authoring environment; `main` is its standalone CLI wrapper. |
| `ruby_bridge` | `contract_from_ruby` compiles and validates the Ruby DSL; `mruby_check` checks embedded Ruby syntax. |
| `workspace` | `workspace_root`, `workspace_path`, and `reject_symlinks` enforce workspace path boundaries. |
| `cli` | `main` dispatches command-line operations and serializes failures as explicit results. |
| `mcp_server` | `tool_specs`, `list_tools`, `dispatch_tool`, `call_tool`, and `main` expose the same deterministic operations over stdio MCP. |

## Determinism and trust

- Gates and triage use explicit model values, not language-model judgment.
- Input paths are normalized workspace-relative paths. Request inputs and
  response artifacts carry hashes so changes are detectable.
- JSON models reject unknown fields at protocol boundaries. Malformed
  request/response/advisory files are reported instead of being accepted.
- File-writing tools declare their side effects; append-only record tools are
  non-idempotent. No MCP tool opens an external network connection.
- `ux-report.json` includes deterministic gate results and separates advisory
  lenses from the verdict.

See [Contracts](contracts.md), [MCP](mcp.md), and
[Records and vision](records-and-vision.md) for exact formats.
