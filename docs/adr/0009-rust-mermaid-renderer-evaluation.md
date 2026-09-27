# ADR-0009: Rust Mermaid renderer (mmdr) evaluation — not adopted

- Status: Accepted
- Date: 2026-09-27

## Context

`mmdc` (mermaid-cli + headless Chromium) is our heaviest render step.
`mmdr` (1jehuang/mermaid-rs-renderer, MIT) is a pure-Rust renderer with
prebuilt linux x86_64 binaries — a candidate to shrink image size and
render time.

## Measured results (mmdr 0.3.1 vs mmdc in ux-tools)

| Diagram | mmdr | mmdc (in-image) | Parsed |
| --- | --- | --- | --- |
| journey.mmd | ~0.01 s | ~1.20 s | both |
| statechart-v2.mmd | ~0.01 s | ~1.44 s | both |
| experience-loops (flowchart LR) | ~0.03 s | ~1.45 s | both |

All 3 of 3 contract projections parsed under mmdr. mmdr SVGs are
5–9 KB vs 210–370 KB for mmdc (mmdc embeds full theme CSS and fonts).
Binary sha256 recorded in the research notes.

## Decision

**Not adopted.** mmdc stays the locked renderer:

- mmdr output lacks Mermaid theme CSS — plainer styling, different look
  from every sibling doc/render.
- Rasterization path is unproven inside our image (mmdr emits SVG/PNG
  directly; mmdc's puppeteer/Chromium path is already exercised in CI).
- Statechart-v2 fidelity beyond the happy path is unverified.

## Revisit criteria

- Theme parity (default/forest/neutral) matching mmdc output closely
  enough for side-by-side renders.
- Verified statechart-v2 and `journey` fidelity on our full example set.
- Release cadence indicating a maintained upstream.
