# Implementation and verification plan

Status: implementation is progressing from the [reassessment](README.md)
and pinned [validation evidence](validation-results.json). The
[review-boundary follow-up](review-boundaries.md) records the implemented
native-identity, coordinator and Stop corrections. Work-package acceptance
below remains distinct from those source changes.

## Order and acceptance model

First reject false bard completion and reproduce review scope leakage with
small fixtures. Then repair reporting and bounded review behavior. Return
to cooperative execution only after these regressions pass. Do not use
another multi-hour eleven-plugin run to discover the same defects.

Track these axes separately:

| Axis | Required fields or states |
| --- | --- |
| Request/response presence | IDs, missing/malformed/stale entries, input/artifact hashes |
| Lifecycle | accepted, in_progress, done, rejected, deferred, needs_info |
| Validation | Subject hash, scope, required checks, tools and evidence paths |
| Check applicability | pass, fail, unknown, not_applicable, with reasons |
| Execution | running, paused, stopped; outstanding gaps and checkpoints |
| Review | Source image hash, owner, reviewer role/session and reconciliation |

Keep SLP v2 compatibility. A response's `done` must satisfy its requested
scope; unavailable checks yield an incomplete/deferred state. `allow` from
a stop hook remains permission to terminate, not acceptance. Visual/audio
observations remain advisory and do not replace deterministic gates.

## Work packages

| ID | Priority / owners | Change | Acceptance |
| --- | --- | --- | --- |
| A | P0 / UX and responders | Separate response presence, lifecycle, verification and execution state | Original fixture reports six responses, three done, three in progress, with bard evidence invalid |
| B | P0 / bard | Bind cue completion to official validation, renderer, provenance and independent output readback | Invalid cue set, empty MIDI, tampered/stale provenance and claimed pass are rejected; valid four-cue rendering succeeds |
| C | P0 / all eleven record hooks; UX review | Bound obligations by plugin owner, run/session, reviewer role and source image hash | Explicit other-session records do not match by time; unrelated images/crops do not create domain obligations; real missing review remains detectable |
| D | P0 / UX orchestration and existing SDK | Finite review budgets, serialized blind review and resumable checkpoints | Exhausted budget stops with gaps; retries terminate; resume skips completed source/role pairs |
| E | P1 / UX, domain/document reports | Typed liaison summaries and subject-aware report selection | Correct counts/root resolution; old dashboard fail remains history; current pass selected by subject/scope |
| F | P1 / eleven plugins | Release-pinned clean installation and minimum cooperation | Actual source/version/image/CLI/MCP/response/gate bindings recorded |
| G | P1 / domain owners | Independently exercise missing feature paths | Required matrix cells have scoped evidence or explicit unknown/N/A |
| H | P2 / domains and website | Improve usability, triage extension requirements and update public claims | Published implemented/planned statements match evidence |

B and C precede D/E integration; B+C+D+E precede F. G proceeds in small
domain units after the corresponding prerequisite. H must not inflate
scope while existing correctness defects remain. Open focused PRs and do
not merge without instruction. Published tags remain immutable.

## B: trustworthy bard cue completion

Inspect the existing responder, official cue validator/renderer and
readback support before adding code. Keep render logic stdlib-only. Reuse
the official contract rather than a second relaxed schema. Verify current
cue-set hash, renderer provenance, generated output hashes, and semantic
readback at the response-writing boundary. User-supplied pass claims cannot
authorize completion. Non-cue requests and incomplete responses need
explicit compatibility coverage.

Required negative cases: the archived malformed schema; 26-byte empty
MIDI; missing provenance; changed cue-set/output; missing declared cue;
wrong BPM/program/duration; and stale or fabricated success evidence.
Each refusal must leave an existing response unchanged and write no new
successful response. Test legitimate rests separately from empty output.

Required positive cases: four official cues, differing tempo and note
lengths, valid MML/provenance, and a repeat run yielding identical bytes.
Parse MIDI independently of renderer serialization; count note-on events,
check timing and mapping, and verify tone-table/PWM handoff separately.
Audio listening and actual device playback are separate validation scopes.

## C: review identity and responsibility

Use the existing VRP/SDK machinery; do not add a custom executor, task
transport or event-history platform. First enforce explicit session
identity: a nonempty mismatched session ID never falls through to the
timestamp comparison. Retain a time-bounded path for legacy records lacking
identity and make its use visible.

Then specify ownership and derived-image metadata at recording time. Each
obligation needs an owning plugin, originating run/session, reviewer role
and source artifact hash. Crops/tiles must reference the original image
revision; their independent existence must not expand the product review
set. A changed original hash creates a new obligation. A path substring
alone is insufficient to declare an image irrelevant.

| Regression | Expected behavior |
| --- | --- |
| Fresh record from explicitly different session | Excluded despite timestamp |
| Identity-free legacy record | Included only inside the documented fallback window |
| UX/bard reviewer observes another domain image | No unrelated domain design obligation |
| Crop/tile read | Associated with source image, no extra product review |
| Original image bytes change | Fresh source-hash review needed |
| Formal output lacks review | Detected; never hidden by broad directory exclusions |
| Blind reviewer has earlier findings available | Independence boundary enforced or reported unknown |

Change canonical shared copies together and refresh each repository's
shared-hook checks with its pinned Python environment. Repository-specific
recording hooks remain specific. Confirm SDK hook inheritance versus
agent-frontmatter hooks against the adopted SDK before relying on either.

## D: bounded work and recovery

The approved [image-review collector](bounded-review-checkpoints.md) uses
one active review pair per checkpoint, 20 native iterations and budget 1.5
per fresh child, two attempts per source/checklist/role, and one explicit
disagreement follow-up. Completed evidence is revalidated and reused;
unfinished pairs receive fresh children without SDK `resume`. These bounds
supersede the initial 20-minute/120-call proposal for image reviews. No
plugin wall-clock timeout is introduced.

Split design, liaison, domain gates, review and collection into checkpoints
containing artifact hashes, response states, remaining work and usage.
Use existing SDK timeout/iteration/cancellation and provider retry/backoff;
respect Retry-After where supported. Do not layer unbounded plugin retries.
After exhaustion, persist paused/blocked state and gaps. Resume only missing
work for the same source revision and reviewer role.

The image-review portion is implemented and locally validated. Broader
design/liaison/domain-stage checkpointing and live provider/backoff timing
remain separate verification work; do not infer their completion from the
synthetic review-collection tests.

Keep bounded stop refusals. Surface their final gap record in status and
reports. Acceptance requires sequential review, finite behavior under
injected 429s, resume without duplicate completed reviews, and an incomplete
run that cannot be displayed as fully accepted.

## E: authoritative reporting

Generate cooperation text from typed liaison state rather than another ad
hoc dictionary. The archived `existing_responses`/`response_files` error
must become a regression case, not a reason to rename a correct public
field. Pass workspace root and product context explicitly to the UX lens;
do not use `out_dir` as the workspace. Resolve root/product liaison entries
by request ID, detecting duplicates, collisions and invalid paths.

Select gate reports by subject SHA and scope. Keep old revisions in history;
conflicting reports for the same subject and scope must be explicit. Show
firmware static success with build/ELF missing, and dashboard's 27 pass /
12 N/A without collapsing N/A into success. Regenerate stale responder
state only after its requested scope actually completes. Preserve the
original six-response fixture unchanged as historical evidence.

## F/G: release and feature verification matrix

Use a separate clean workspace after preserving existing evidence. Record
actual installed release/tag/source SHA, SDK/AgentCanvas/model capabilities,
image digest and attestation state. Confirm eleven plugin loads separately
from tool readiness. Run a minimal UX contract, liaison cycle, scoped domain
gates, bounded primary/blind/reconcile review, and complete evidence export.

| Order | Domain | Required evidence |
| --- | --- | --- |
| G1 | Bard | Official validator, independent MIDI readback, MML/provenance and device tone mapping; positive and negative cases |
| G2 | Circuit | Real schematic/PCB, ERC/DRC, routing/Freerouting, exports; deliberately invalid circuits rejected |
| G3 | Firmware | Existing profile, circuit handoff, build log, non-null ELF hash, QEMU/simulation; static success remains distinct |
| G4 | Mechanical/wire | STEP/DXF readback, interference/DFM, multiple connectors/anchors, keepouts and formboard |
| G5 | UX | Every supported projection generated/parsed; image render/hash/review mapping; N/A reasons |
| G6 | mruby/c chain | UX API contract to firmware C/H, compile/run, sim/dashboard stubs; POSIX is not WASM/device proof |
| G7 | Dashboard | Telemetry/ack/hazard behavior, runtime checks, WASM parity and applicable Playwright/platform/transport paths |
| G8 | Simulation | Solver raw output to parse/bounds/plot; optional RF solvers independently provisioned and assessed |
| G9 | Document/prodeng | Correct sister evidence, page/figure rendering, long and multilingual documents; renderer gaps explicit |
| G10 | FPGA | Synthesis/place-route/simulation/full gates, bitstream; reject bad constraints; programming requires separate human confirmation |

For each cell record repository SHA, install source, image digest, input
SHA, invocation, exit code, report path/subject/scope, output hashes, review
references and unresolved gaps. Use repository launchers and digest-locked
images for Docker-only domain execution. CI/lint/unit success does not
substitute for a missing platform, real solver or physical device test.

## H: decisions after correctness work

Doctor/prewarm should show missing images, expected preparation and a
retryable next command without weakening fail-closed attestation checks.
Validation messages should include small valid examples, not encourage
boilerplate record padding. Compare reuse of a sister renderer with a
pinned document image before choosing a new renderer/dependency.

Decide optional openEMS/kicad-rfsim publication using actual precision,
usage and CI cost requirements. Triage CJK fonts, long-page production
documents, PFMEA AP, multi-board geometry, hinge/detent features, KBL/VEC
and `.frd` field plots as separate requirements. Inventory the existing
39 MCU profiles before adding duplicate profiles. Update website claims
after evidence exists; raw workspace conversations/logs stay private.

## Final acceptance and handoff

Report changed repository/revision, verified matrix cells, unknown/N/A
scope, outstanding gaps and required maintainer decisions in one index.
Completion of B/C/D/E establishes corrected minimum-flow behavior only
after release-install verification. It does not establish completion of
all G cells or physical product acceptance. Retain failed attempts and
original artifacts alongside later successful evidence.
