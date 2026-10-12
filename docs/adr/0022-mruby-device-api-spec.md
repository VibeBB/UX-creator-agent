# ADR-0022: UX-authored `*.mruby-api.json` device API specs

## Status

Accepted

## Context

Products embedding mruby/c expose device-specific classes and methods
(OpenBlink's `src/api` is the reference). The API surface — names,
keyword shape, enums, docs — is a UX decision, while argument decoding
and marshalling are firmware work. A single JSON document needs to feed
both: UX authors it, firmware generates C bindings from it, simulation
and dashboard generate stubs to run UX `.rb` logic off-target.

## Decision

`api/<name>.mruby-api.json` (`artifact_kind: "mruby_api"`,
schema_version 1) declares classes, methods (positional/keyword params,
`**rest`, trailing blocks), constants, instance classes with
constructor/destructor handlers, and access levels (`any`,
`system_task`, `expert`). The schema mirrors `firmware.mruby_api`
field-for-field — the JSON is the contract, never shared code.

`python -m ux_creator mruby-api <spec>` runs the UX-side gate:
Ruby-idiom lint (doc lines, `?`/`!` conventions, `get_`/`set_` bans,
≤3 positional args, `on_*` blocks, symbol `enum`s), manifest class
collisions, and `*.rb` usage coverage (call sites and symbol literals
must be declared). Without `--check` it renders the API reference
`<name>.mruby-api.md`.

The `*.mruby-manifest.json` now lists the classes ux `*.rb` sources
define, letting firmware reject name collisions between Ruby-defined
and API-declared classes.

## Consequences

- Ruby-ness is enforced deterministically before firmware ever sees a spec.
- Typos like `LED.toggel` fail at authoring time, not at firmware compile.
- The rendered doc is the user-facing API reference; `doc` fields are required.
- firmware/simulation/dashboard consume the same spec file — one surface.
