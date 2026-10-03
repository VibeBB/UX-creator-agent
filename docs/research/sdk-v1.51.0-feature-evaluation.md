# OpenHands SDK v1.51.0 feature evaluation (UX-creator-agent)

Scope: `openhands-sdk` and `openhands-tools` move from 1.50.1 to 1.51.0
(PyPI upload 2026-10-03T07:38Z); the complete upstream range
`v1.50.1..v1.51.0` was reviewed. uv moves 0.12.21 -> 0.12.22 (required-version
plus the `astral-sh/uv` image ARG/digest in `docker/ux-tools.Dockerfile`).
ruff was already resolved at 0.16.10 in `uv.lock` (latest of the `>=0.16`
line); no spec change was needed.

Primary sources: [OpenHands SDK v1.51.0 release](https://github.com/OpenHands/software-agent-sdk/releases/tag/v1.51.0)
([compare](https://github.com/OpenHands/software-agent-sdk/compare/v1.50.1...v1.51.0)),
[uv 0.12.22 release notes](https://github.com/astral-sh/uv/releases/tag/0.12.22).

## SDK 1.50.1 -> 1.51.0

| Upstream change | Decision | Evaluation |
| --- | --- | --- |
| #5151 agent-profiles: `tools` is the only tool control, selected from one server catalog | already aligned | Plugin AgentDefinitions declare `tools:` lists (`terminal`, `file_editor`, `grep`, `glob`, `task_tracker`, `task_tool_set`); the retired switches `enable_sub_agents`/`enable_switch_llm_tool` (deprecated 1.51.0, removal 1.56.0) were never used. `check_plugin_load.py` passes unchanged. |
| #5358 delegated sub-agents stay within the profile's tools/MCP servers | adopted implicitly | Matches how `task_tool_set` delegation is expected to behave for `ux-creator`/`ux-liaison`; no plugin change. |
| #5434 deprecate `ACPAgentSettings.llm`; related settings/model deprecations | not applicable | No ACP agents and nothing sets the deprecated fields (`ACPAgentSettings.llm`, `system_prompt_kwargs['enable_browser']`). `check_plugin_load.py` uses `register_default_tools(enable_browser=False)`, a separate supported argument. |
| #1326 fix `find_dotenv` assertion error in local conversation | adopted with the pin | Plugins run `LocalConversation`; removes a crash path. |
| #5332 resolve `prompt_cache_key` via the real provider for proxied models | adopted implicitly | LiteLLM-proxied `vibebb-*` profiles benefit; no profile change. |
| #5274 make OpenRouter a verified provider | not adopted | No `vibebb-*` profile uses OpenRouter today; the provider is available for future profiles without repo changes. |
| #5449 let a profile replace the agent's persona | not adopted | VibeBB profiles only provision LLM credentials via `ensure_llm_profiles.py`; personas stay repo-owned. |
| #5406 launch every agent through resolve/finalize; #5450 loaded tools supply system-prompt guidance | internal | Behavior under the same APIs the plugin load check exercises; no repo change. |
| #5412 router classifier messages; #5417 `/switch_llm` provider resolution; #5397 stress-run slot | upstream image | agent-server/CI-side changes; this repo does not run an agent-server. |
| #5419 pydantic 2.12.5 -> 2.13.5 upstream | lock-only | `uv.lock` already resolves pydantic 2.13.5. |
| #4945, #5415, #5425, #5428 upstream CI/TypeScript dependabot; #5470 release housekeeping | not applicable | No TypeScript client or upstream CI usage in this repo. |

## uv 0.12.21 -> 0.12.22

| Upstream change | Decision | Evaluation |
| --- | --- | --- |
| New managed CPython builds (3.10.22, 3.11.17, 3.12.15, 3.13.16, 3.14.8) | inherent | `uv python install 3.12` resolves the newest 3.12.x on the next image build; no pin change. |
| Lockfile records workspace-member default groups and dependency-group Python requirements | n/a | This repo is a single project, not a uv workspace. |
| Re-lock verifies unchanged requirements against existing lockfile hashes | inherent | Hardening on `uv lock`; already exercised by `uv lock --upgrade`. |
| `UV_PYTHON_ARCH` env var selects interpreter architecture | not adopted | The image and CI are single-arch x86_64; nothing cross-arch installs interpreters. |
| Uppercase wheel platform-tag suffixes; consistent URL/path CLI formatting; `uv publish --offline` hidden; compressed embedded Python metadata | inherent | No publish/audit usage and no reliance on message formatting. |
| `uv audit`/`uv tool audit` preview flags (`--no-default-groups`, offline error) | n/a | Preview features are not enabled. |
| MSRV raised to Rust 1.97 (toolchain 1.99) | n/a | Prebuilt `astral-sh/uv` binaries; uv is never built from source. |

## Compatibility deferrals

MCP 2.x remains deferred: installed `openhands-sdk` 1.51.0 metadata still
requires `fastmcp>=3.2.0,<4`, which caps `mcp<2` (resolved: 1.30.0). The
deferral entry's `latest` was refreshed to 2.3.0 and its reason re-pointed
to SDK 1.51.0; `review_by` is unchanged (2027-04-01).
