# Cooperative-run reassessment

Evidence cutoff: 2026-11-15. This is an investigation of an existing
11-plugin AgentCanvas run and its subsequent research/release work, not a
new execution of every product feature. The [implementation plan](implementation-plan.md)
separates proposed changes from verified results. The
[validation summary](validation-results.json) binds the figures below to
the privately delivered evidence archive and pinned repository revisions.

## Conclusion

All eleven plugins loaded, and selected CLI/MCP operations and artifact
handoffs worked. This does not establish completion of every request,
coverage of every feature, or acceptance of a physical product.

The most consequential finding is a false completion claim: bard returned
`done` and declared a cue-schema pass although its saved cue set was
rejected by the official validator. All four saved MIDI files were the
same 26-byte empty track, with no note-on events. The event that wrote
them explicitly generated placeholders. The official renderer contains
note-on/note-off generation; the defect is the ability to acknowledge
completion without establishing that the official rendering path ran.

Long review sessions had several interacting causes. The UX status hook
returned `allow` on all 27 observed invocations and reported unreviewed
images once. Shared record hooks produced 32 stop denials, 27 in child
conversations, including obligations for other plugins' images and
temporary crops. Changing only UX's directory scan would leave these
ownership and session-boundary problems unresolved.

## Evidence and acquisition coverage

| Evidence | Observed coverage | Interpretation limit |
| --- | --- | --- |
| Original attachments | Six preserved, including the original reports and workspace | Acquisition does not validate their conclusions |
| Original workspace | 398 regular files; 16,167,688 bytes | Directory entries and expanded temporary files use different counts |
| Recovered workspace | 3,363 files; 46,160,012 bytes | Includes 2,965 temporary files: 2,305 JSON and 660 PNG |
| Original/recovered comparison | All 398 original files have identical SHA-256 | Later temporary files are additional evidence |
| Parent and three child conversations | 59,709 events: 29,027 + 11,820 + 10,238 + 8,624 | All four ended paused in the recovered snapshot |
| Liaison bindings | 25 input/artifact references match existing bytes | Hash agreement does not establish semantic correctness |
| VRP chains | 1,376 v2 records checked without hash/link mismatches | Does not prove factual accuracy or review independence |
| Original visual artifacts | 34 PNG and 18 SVG decoded and indexed | Static artifact inspection; not new UI testing |
| GitHub source | Twelve pinned main snapshots; recursive trees untruncated | Point-in-time source evidence, not a complete history mirror |
| Release assets | Seventeen ZIPs across ten new releases; CRC and published digests match | Not a clean-install cooperative test of those releases |

The original standalone GUI screenshots could not be recovered because
their storage directory no longer existed. One historical UX Release
run's log download returned HTTP 404. These remain explicit evidence
gaps. Generated desktop/mobile artifact PNGs are not substitutes for
screenshots of the original interactive session.

The recovered parent events directly show one `MaxIterationsReached(500)`
and one `LLMRateLimitError`. The earlier claim of two 500-iteration
failures is not substantiated by those parent error events. Three parallel
review children preceded rate limiting; provider quota/usage evidence is
insufficient to establish concurrency as the sole cause.

## Findings and source anchors

### F01: Completion can outlive valid generated evidence (P0)

Six requests had six responses, but only three responses said `done`;
three remained `in_progress`. Bard's `done` was additionally unsupported
by valid cue artifacts. Count existence, lifecycle status, input hash,
validation scope, and verified completion separately.

The [bard responder](https://github.com/VibeBB/bard-agent/blob/a36aa5d61abb2686be5412eb6978aca81445389c/plugins/bard/scripts/bard_liaison.py)
and [official cue renderer](https://github.com/VibeBB/bard-agent/blob/a36aa5d61abb2686be5412eb6978aca81445389c/plugins/bard/skills/bard-render/scripts/render_cues.py)
are the implementation boundaries to strengthen. Require current cue-set
and output hashes, official validation/rendering, provenance, and readback
before emitting a successful cue completion response. A user-supplied
`gate_verdicts` entry is not proof of execution.

### F02: Review obligations cross session and ownership boundaries (P0)

The [shared record hook](https://github.com/VibeBB/UX-creator-agent/blob/d52d620b3baba121a619b4553ce20ad565c61ee1/plugins/ux/hooks/scripts/require_records.py)
accepts a record whose explicit session ID differs when its timestamp is
new enough. Explicit identity mismatch must not become a timestamp-only
match. Legacy records without identity need a bounded compatibility path.

Image observations and changed artifacts also need distinct responsibility
rules. A plugin should not create a new domain review obligation for every
image seen by an unrelated reviewer. Derived crops/tiles need their source
image hash and role, rather than independent product-artifact obligations.
Selected runtime hooks matched the pinned source in all 23 compared files.

### F03: A bounded stop allowance is not acceptance (P0)

After a finite denial budget the shared hook allows termination and records
gaps. Preserve that bounded exit, while exposing unfinished obligations in
the final state. Distinguish stop permission, run completion, deterministic
acceptance, and acceptance with recorded gaps. Hash chains and reconciled
review records alone do not prove blind-review independence.

Repeated review is measurable: production engineering had 335 review
records over 105 distinct images, with a maximum of 41 records per image;
UX had 245 records over 82 images, maximum 13. Restrict work by source
revision and reviewer role, checkpoint progress, and resume missing work.

### F04: Reporting loses typed state and subject identity (P1)

The cooperation report's zero-response count came from a generated command
reading `existing_responses`, while its input contained `response_files`.
This was an ad hoc report-generation defect, separate from the core
[UX liaison lens](https://github.com/VibeBB/UX-creator-agent/blob/d52d620b3baba121a619b4553ce20ad565c61ee1/src/ux_creator/report.py),
which uses the output directory as its workspace/search root.

Dashboard's pass and fail reports describe different contract hashes:
the current pass uses `2d8bb4befaf780e0cfb34865a0751425d7f2b1f8406435e55ca37ecb95e59a26`;
the old fail uses `b18327eddf3ef0620fd454787d828f57c7bf7e0b42d89fa1873877ac73c6c273`.
Retain historical reports while selecting authoritative results by current
subject hash and scope. Do not describe these as contradictory judgments
of the same revision.

## Domain results and limits

| Domain | Evidence present | Unverified or limited scope |
| --- | --- | --- |
| UX | Contract, 21 gate passes, selected renders, six requests, three reviewed images | All projection formats, full image manifest, mruby handoff chain |
| Circuit | Brief/connectivity and firmware export | Response in progress; ERC/DRC unknown; schematic/PCB/routing not established |
| Firmware | Seven static checks; contract and pinmap | `scope=static`, null ELF hash; build/QEMU/device behavior unknown |
| FPGA | Full report: eleven pass, two N/A; bitstream/nextpnr evidence | Formal N/A; hardware programming untested; keep static/full reports distinct |
| Mechanical | Thirty-nine gate passes; STEP/DXF/envelope/projections | Response still in progress; not FEA or manufacturing acceptance |
| Wire | Forty-eight gate passes; harness and drawio output | Near-single-anchor route example does not validate complex routing |
| Simulation | Four checks and PDN/thermal/lifetime/SPICE output | openEMS/kicad-rfsim unavailable; a no-data plot is not analysis evidence |
| Production engineering | Thirty-one checks and production documents | PFMEA AP, long-page and multilingual boundaries remain separate work |
| Dashboard | Current full report: 27 pass, 12 N/A; typecheck/test/WASM parity | Tauri, mruby/c WASM, WebMCP and physical transport not established |
| Document | Liaison, lint, figures and Markdown | Renderer gaps and report content accuracy need independent checks |
| Bard | Plugin/record/liaison flow | Invalid cue set; silent placeholder MIDI; no verified rendering/audio/device path |

The definition inventory contains 101 skills (78 keyword skills and 23
path rules) and 79 commands. Definition count is not feature-execution
coverage. Map definitions to actual invocation, validator, output, failure
case, and gate scope before computing a coverage percentage.

## Reassessing earlier improvement notes

| Earlier direction | Reassessment |
| --- | --- |
| Release ten siblings as v1.0.0 | Already completed in the later session; do not repeat or retag |
| Firmware has only two profiles | Stale: pinned source has 39, including eight STM32 and six Nordic profiles; build/device coverage is still unknown |
| UX SLP producer is unimplemented | Stale relative to current source and recovered requests/responses; repair the observed flow |
| Simulation has no FEM plot | Too broad: cantilever curves exist, with CalculiX or analytic-tip input; `.frd` stress/displacement field plots are a separate gap |
| Ignore temporary image directories | Insufficient alone: ownership/session/source mapping must preserve real artifact obligations |
| Increase global iteration limits | Prefer bounded phases, explicit budgets and resumable checkpoints |
| Automatically prewarm everything | First show missing images, pull requirements and the next command; retain attestation requirements |

Installed runtime versions were bard 1.1.0 and ten siblings at 0.1.0.
Published versions were bard 1.1.0 and ten siblings at 1.0.0. Hook parity
does not establish whole-plugin parity. A release-pinned clean-install
regression remains necessary after the fixes.

## Preservation and reproduction boundary

The [review-boundary implementation follow-up](review-boundaries.md) records
subsequent identity, coordinator and Stop corrections and their verification
limits. Those source changes do not alter the historical findings above.

The [image-identity foundation](image-identity-foundation.md) describes the
first C3 producer/path/SHA binding at the MCP image boundary. The
[observation delivery correction](image-observation-delivery.md) preserves
those claims and the actual delivered revision in the native observer log. The
[native SDK limit probe](sdk-native-review-limits.md) records the D-stage
resume limitation and the decision still required before adopting a
checkpoint strategy.

The complete raw conversations, operational logs, original attachments,
workspace, runtime hooks, pinned source archives, audit scripts, Japanese
reports and image atlas remain in the user-delivered research ZIP. They
are not published in this repository. The user approved publishing this
technical assessment, plan and aggregate validation evidence here.

That archive contains 730 payload files plus its SHA-256 manifest; its
121,067,176 bytes have SHA-256
`610bd3578910ba20d9a9a55a0fda2672079dfc1f08c946fd877cbeccbcb6a723`.
ZIP CRC, every manifest member, and the archive sidecar digest passed.
An independent extracted copy restored all five expanded evidence trees
and reproduced the principal offline audits. Aggregate results here are
not a replacement for that private artifact evidence. Original evidence
is retained unchanged when later implementation results are added.
