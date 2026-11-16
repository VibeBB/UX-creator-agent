# Fixed-release domain verification and handoff

This follow-up separates the historical run from new fixture executions.
It records the G1–G10 work in the [implementation plan](implementation-plan.md),
including failures, corrected reruns and unavailable paths. The work does not
establish a completed eleven-agent product workflow or product acceptance.

The [release lock](family-release-lock.json) fixes eleven source commits and
release tags. The [installation procedure](family-installation.md) explains
clean asset installation and the different Bard/Document runtime boundaries.
The [machine-readable evidence index](family-domain-validation.json) contains
the original recorded invocations, exits, image digests, input/report/output
hashes and retained file inventory. Paths beginning with `out/` identify
payloads in the private evidence attachment, not files published to Git.

## Evidence and interpretation

The clean fourth installation has lock SHA-256
`13072c63fe07abd3b8eca4355bc0a6e5f8c7e45dd047ce24099379ff846f72dd`.
All eleven asset trees load. Ten declared MCP backends initialize; nine use
published digest-locked images without host source overlays, and Document
uses installed stdlib scripts. Nine sister MCP request/response/staleness
cycles succeed with `in_progress` responses. Acknowledgement is not completed
domain work. Earlier failed cycles remain in the index.

Bard is intentionally CLI-only. Its pinned v1.1.0 release lacks
`bard_cli.py`, `bard_liaison.py` and `bard_records.py`. The corrected installer
therefore exits 1 even though all assets load. A separately identified
current-source Bard CLI cycle passes at commit
`566dcd4868254212838c92d1ffbe9be523b71431`, also returning `in_progress`.
This cannot be substituted for the missing released CLI.

The raw supplement is `family-domain-evidence.zip`, 15,893,018 bytes,
1,986 payload files, SHA-256
`53e5621bc008d18ed9bdad73421697251a0893618b135f8ccb0795798d530aeb`.
Its CRC check passed; `ARCHIVE-MANIFEST.json` binds every payload to bytes.
It preserves relevant contracts, outputs, reports, probe scripts and logs;
reproducible dependency/build caches are excluded. Complete historical
conversations remain in the previously delivered private archive. Neither
archive is committed to this public repository.

File-inventory hashes describe the final preserved snapshot. A trial's
recorded `log_sha256` describes that invocation. If a renderer later
regenerated a file, the final file hash does not retroactively become the
original invocation's output hash. Separate directories retain the important
Dashboard, UX and FPGA failures and their successful reruns. Some older
host-script probes have output logs but no structured command/exit record;
those fields remain unrecorded rather than being reconstructed as observed.

## G1–G10 matrix

The index associates each cell with pinned source, runtime, reports, images
and gaps. The table summarizes the actual scope; a fixture pass does not
mean that every feature in the row is covered.

| Cell | Evidence established | Retained failures and limits |
| --- | --- | --- |
| G1 Bard | Released song renderer produces English/Japanese ABC, MIDI, MML and provenance. Independent `mido==1.3.3`, ABC-to-MIDI and MML/proposal readers agree on melody pitch/timing within the documented ABC gate-length tolerance. Current-source four-cue output has matching MIDI/MML, frequencies and cumulative millisecond tone boundaries. | Released SLP CLI unavailable. Cue completion rejection tests belong to current source, not v1.1.0. Original invalid cue/empty-MIDI evidence remains historical. Original outer shell command/exit for the song-render probe was not structured; logs and output hashes are preserved. No listening or physical buzzer validation. |
| G2 Circuit | `led_loop` fixed-image authoring report passes; schematic/PCB/render artifacts, ERC/DRC and exported connectivity are preserved. A separate reader checks the real exported netlist and rejects a removed component. | Small fixture only; manufacturing, analog accuracy and arbitrary board designs are not accepted by this result. The negative probe's exit 0 means its rejection assertions passed, not that the mutated design passed. |
| G3 Firmware | Full reports pass for ESP32-S3 desk-lamp and nRF52840 mruby-UX, including build, ELF hashes and named simulation transcripts. | Two profiles exercised; all 39 profile JSONs are inventoried, not all built. Real boards, peripherals and timing remain unknown. |
| G4 Mechanical/Wire | Enclosure and sensor-harness generation/gates pass; formboard is generated. Independent fixed-image STEP import finds valid positive-volume solids in four files; two DXF files have nonempty modelspaces and zero audit errors. | Mechanical's original sample intake SHA is stale and a focused PR corrects it. Valid STEP topology does not prove physical fit, structural performance or manufacturability. Harness PNG/formboard review is advisory. |
| G5 UX | Basic UX authoring passes. Product fixture passes when run with its actual imported Bard evidence in the owning workspace; Mermaid/PlantUML projections are generated. | Initial product run fails because its relative Bard import is absent from that workspace. Preserve that report; do not turn a context error into an unconditional success. Projections are design artifacts, not a finished interactive product. |
| G6 mruby/c chain | The same API bytes and Ruby bytes used by the firmware fixture run in the fixed Simulation and Dashboard images with Emscripten/Node WASM. Both exit 0 and contain all five expected state/API transcript markers. Firmware bindings/build/simulation are evidenced separately by G3. | Three earlier attempts fail due to entrypoint/result handling, Simulation mount identity and Dashboard Emscripten-cache identity. All are preserved. No claim that these stubs prove a real device implementation. |
| G7 Dashboard | Corrected full `smart-kettle` report passes: 32 runtime tests, WASM parity, 14 repository Chromium tests, captures and Servo smoke. Runtime evidence covers telemetry, matching ACKs, disconnected/timeout behavior and hazard confirmation. | Initial full report fails Chromium tests. The later report has the same contract SHA and a separate path. Tests use mocks for hardware transports and browser emulation for platform cases; no native iOS/Bluefy/BSD or physical device acceptance. Servo passes its smoke criteria while its log still contains `uncaught exception: undefined`; a clean error-free browser session is not established. |
| G8 Simulation | Buck-regulator fixture passes real ngspice/CalculiX, import provenance, parse/bounds checks, plots and mruby/c transcript checks. RF Touchstone input and analytical microstrip checks are exercised. | Initial plot lookup used the wrong hyphenated output name; corrected lookup uses `buck_regulator`. No optional openEMS/KiCad-rfsim solver execution. No `.frd` field parsing or full-field stress plot; the deflection curve is narrower evidence. |
| G9 Document/Prodeng | Released full Document lint passes desk-timer manual/reference and launch documents, preserving source hashes. Production kettle authoring/report and ten production-sheet PNGs pass/generate. | Document reports still contain one open question and one unanswered inquiry each. No pinned Document page/PDF/CJK renderer exists in this evidence. Production's small deterministic raster sheets do not prove long-page/CJK typography or document pagination. No completed native documentation/manufacturing workflow or physical factory acceptance. |
| G10 FPGA | Five example targets have successful full reports across Tang Nano 9K/20K, Tang Primer 20K, ULX3S and IceBreaker UART after the stated retries. Synthesis/place-route, bitstream hashes and applicable waveform outputs are preserved. Invalid device pin is rejected with exit 1. | Initial NVC relative waveform paths fail for two Gowin fixtures; absolute-path reruns pass and source fix is in a separate PR. IceBreaker initially lacks pinned Colibri and passes after that declared dependency is fetched. Hardware programming remains outside agent gates and was not performed. |

G7 executes the repository's existing shell-driven automated gates; there was
no separate Devin UI testing-agent run or user acceptance session.
`not_applicable` fields (for example no optional Dashboard WASM module,
factory view or i18n section in that contract) are not additional passes.

## Shared API identity and preserved attempts

The G6 API SHA-256 is
`f011c9e2fba8db3c359f698a14d55b4e739d91bc6c22d4b9b4fd8b9926a5a81b`;
the Ruby SHA-256 is
`a10e5ffb54913c92cddcff31b0717f3957c049a34b16a70ffa680af09d110557`.
The successful `out/shared-api-wasm-04/result.json` records:

| Runtime | Fixed image digest | Exit |
| --- | --- | --- |
| Simulation | `sha256:baecce874ff2ed01d18abe4b4c6c25dd23cece4d1a1a075c26da5b89697a7534` | 0 |
| Dashboard | `sha256:e5c1751caa8d62a10937174cddcb658c03e2c0c6057c1f1e808a4e75386fbe15` | 0 |

Both containers use `--network none` and `--entrypoint python3`, retaining
their installed domain modules. Only Simulation needs the host UID/GID for
the bind-mounted output; Dashboard uses its image identity so Emscripten can
lock `/opt/emscripten-cache`. Attempts 01–03 and their individual logs are
retained separately. This is fixed-image execution, not a host substitute.

## Visual inspection scope

[The visual inventory](family-visual-review.json) binds 118 PNG paths to
90 distinct SHA-256 values and eight contact sheets. Every distinct image
was inspected at contact-sheet scale; the two English/Japanese score PNGs
were also inspected at full size on a white background. Their transparent
black notation initially appeared black-on-black in an RGB contact-sheet
conversion; only the preview compositing was corrected, not the originals.

The image attachment `family-domain-images.zip` (29,849,867 bytes,
248 entries) has SHA-256
`a28af71de935d812f507410ef0ca742af755c6da9022c19712d6bf9b4719fce4`.
Its manifest includes PNG/SVG/PDF artifacts and previews. Important observations:

- Dashboard images show the idle/no-device state and transport limitations;
  the Servo framing does not establish a complete supported device UI.
- UX diagrams contain small/pale labels; the overview is insufficient for
  detailed readability, accessibility or pagination acceptance.
- Mechanical projections and wire formboard are visible; independent geometry
  checks, not visual appearance, establish the narrow topology result.
- Historical failed FPGA reports are deliberately visible alongside corrected
  runs, not hidden or counted as newly accepted images.

This inspection created no native VRP review records. A path, producer,
returned-image observation or SDK vision event cannot establish which image
the SDK model selected. Native image selection/perception, audio perception,
physical operation and overall `acceptance` remain `unknown`.

## H: usability and extension triage

The installer now prints available installed prewarm commands as argument
arrays and actionable recovery steps. It distinguishes a missing native CLI,
missing MCP entry point, source-integrity failure and image preparation;
Document has no image prewarm. Rerun into a new output directory after fixing
the reported cause. Do not bypass attestation or synthesize image locks.
The [installation guide](family-installation.md) documents the retry sequence.

These are requirement assessments, not newly shipped feature claims:

| Item | Existing capability / gap | Recommendation and acceptance needed |
| --- | --- | --- |
| MCU profiles | 39 fixed-release JSONs, each inventoried by path and SHA; only two builds tested here. | Reuse an existing profile before adding one. Broader support needs the target SDK/toolchain and a named build/simulation fixture. |
| CJK and long documents | Document lint is stdlib-only and validates Markdown/source evidence. Production renders fixed raster sheets; it is not a general font/pagination engine. | First reuse sister-generated figures by SHA. For actual paginated manuals, specify paper sizes, page count, CJK fonts/licences and layout acceptance, then choose a pinned renderer with an ADR. Merely installing another renderer would not close the typography gap. |
| Renderer reuse versus new image | Existing UX diagram images avoid a second renderer; Production's raster text is narrow; neither demonstrates long-form Document pagination. | Keep Document's current dependency boundary. Prefer reused diagrams for present fixtures. Add a dedicated pinned Document image only for an approved page/PDF requirement with measured startup/image/CI cost; do not silently make it mandatory for Markdown lint. |
| Optional openEMS/KiCad-rfsim | Main Simulation image probes availability; optional EM image pin is reserved/null. Existing RF fixture uses Touchstone/analytical checks. | Do not label EM solver support release-ready. Select a reference antenna/port/mesh, accuracy bounds, reproducibility and CI resource budget before publishing and pinning that image. |
| `.frd` fields | CalculiX `.dat` deflection parsing exists; `.frd` fields are not parsed. | Specify supported element/result types, units, reference mesh and tolerance before adding field plots; a deflection curve is not a field solver proof. |
| PFMEA AP | Production emits `rpn_informational`; that is not AIAG/VDA Action Priority. | Obtain the applicable method/table rights and product scoring policy before implementing AP; do not invent an AP table or infer certification from RPN. |
| Multi-board geometry | G2 exercises a single board and G4 an enclosure, not assembly collision/alignment. | Require named board transforms, connector mating, clearance tolerance and an assembly fixture before claiming multi-board support. |
| Hinge/detent | Mechanical models snap-fit/rib/boss features; its source explicitly describes living hinges and detents as parametric rule checks only. | Retain that label. Modeling needs material/process/geometry constraints and a geometric readback fixture; physical cycle life remains separate. |
| KBL/VEC | Wire accepts normalized JSON tagged `kbl`/`vec`; `load_connectivity_source` reads JSON. This is not a native XML KBL/VEC importer. | Specify interchange versions, units, mapping and redistribution-safe fixtures before adding XML parsers; fail on unmapped required connectivity. |
| Website claims | The website repository is outside the authorized eleven repositories. | Public UX wording is updated here; hand off these exact evidence limits to its maintainer without changing that repository. |

## Implementation and maintainer handoff

The [PR/revision snapshot](family-implementation-status.json) records the
seventeen implementation PR heads and check outcomes before this documentation
commit. At that observation all are open, no checks are pending or failed, and
review findings have recorded fixes. Live PR checks remain authoritative for
later commits; open PR work is not described as merged into `main`.

| Package | Delivered | Remaining acceptance boundary |
| --- | --- | --- |
| A/B/E reporting and completion | Historical counts corrected; Bard official cue evidence and Dashboard subject/scope checks; focused fixes and regression evidence. | Historical false `done` is retained as invalid evidence. |
| C owner/derived images | UX auxiliary-image identity and eleven-plugin record/Stop integration, including distinct vision-event and image-observation IDs. | Delivery/provenance is not native perception. |
| D bounded work | Image-review and design/liaison/domain checkpoints; SHA-bound reuse, fresh bounded children, interruption recovery and finite attempts. | Live provider service behavior/backoff is not established by deterministic injected cases. |
| F installation/cooperation | Clean fixed-source inventory, ten MCP initializations, nine SHA-bound sister acknowledgement/staleness cycles; separate current Bard CLI probe. | Released Bard SLP unavailable; eleven completed native workflows remain unknown. |
| G domain verification | Every G cell has scoped evidence and explicit gaps above; failures and output identity preserved. | Device/audio/physical acceptance, exhaustive profiles/platforms, long-page/CJK and optional EM execution remain unverified. |
| H usability/public wording | Preparation/retry guidance and accurate public claims; renderer/solver/profile/feature triage. | New methods require their stated requirements; no speculative feature is marked implemented. |

Recommended maintainer sequence: review and merge the independently tested PRs;
publish a new immutable Bard release containing its native SLP CLI and the
appropriate updated family releases/images; refresh the release lock only
after those assets exist; repeat the bounded minimum workflow from that new
lock. Merging, releasing and programming hardware were not performed here.
The fixed historical lock remains unchanged for reproducibility.
