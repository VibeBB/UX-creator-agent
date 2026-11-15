# D: native SDK task resume limit probe

## Method

An offline probe used the installed OpenHands SDK 1.62.0 `TaskManager` with
the shipped `ux-blind-review` agent definition. It exercised the actual
`_create_task`, `_evict_task`, and `_resume_task` path, inspected conversation
state, and retained a sentinel message across resume. For isolation the
definition used an inherited in-memory LLM and empty MCP configuration.
No conversation run or provider call was made. This inspects configured
limits and persisted context; it is not an exhaustion or cancellation test.

Five independent repeats all exited successfully and produced:

| Observation | Fresh task | Resumed task |
| --- | --- | --- |
| Configured iteration limit | 20 | 500 |
| Configured budget limit | 1.5 | 1.5 |
| Native conversation identity | Created | Same identity |
| Sentinel message | Present | Retained |

The parent was deliberately configured with a different iteration limit
(7) and budget (0.25). Fresh tasks used the definition's 20/1.5 limits.
Resume reconstructed the child with the default 500-iteration setting;
the budget and event history persisted. SDK `_create_task` forwards the
definition's iteration setting, while `_resume_task` omits it when creating
the restored `LocalConversation`.

Private evidence preserves the executable probe, driver, per-repeat JSON,
logs, CSV, command arguments, durations, source digests, and failed import
attempt. Probe SHA-256:
`00134aff0a51cddb7489b752749b64b958bfbc3f41186d77a707d6981eba60f2`.
Driver SHA-256:
`cab2b9a1a1318bd0313cd2f54651efd9b78f153c640b9f64d2a6bdfc9b428523`.
Raw session identities and logs are not published here.

## Decision boundary

The configured budget surviving does not preserve the 20-iteration bound.
Do not describe same-child resume as bounded by that agent definition on
this SDK version. Live provider spending, MCP startup, exhaustion handling,
wall-clock cancellation, and review quality were not measured.

The proposed alternative is a coordinator checkpoint that reuses completed
reviews by source revision and creates a fresh native child for each
unfinished image/reviewer pair. Fresh children apply the definition limits
without preserving the earlier child's message history. This is a proposed
design awaiting the user's choice; it is not implemented by the image
identity change. Same-child history requires a supported SDK fix or version
that preserves the definition limit. No SDK patch, custom executor, task
transport, or event-history platform has been introduced.
