# mruby-ux device API

Generated from `mruby-ux.mruby-api.json` — the UX-authored contract.

## `LED` (class)

On-board status LEDs driven by the UX state machine.

### Constants

- `LED::OFF` = `0`
- `LED::ON` = `1`

### Methods

- `LED.set(part:, state:)` → `bool`
  - Set one LED state by part.
- `LED.toggle(part)` → `bool`
  - Toggle one LED, returning the new state.
- `LED.all(states)` → `int`
  - Set every LED from a state array.
- `LED.dump` → `string`
  - Dump LED state for the system task.
  - Access: `system_task`
- `LED.raw(idx, level)` → `nil`
  - Expert-only raw brightness control.
  - Access: `expert`
- `LED.on_change(**rest, { ... })` → `nil`
  - Register a change callback block.

## `Sample` (class)

ADC sample source with per-instance driver state.

Instance class: `16` bytes of driver state per object.

### Methods

- `Sample.read(ch)` → `array<float>`
  - Read a channel, returning float samples.

## Symbols

- `:led1` → handler constant `kFwHwLed1`
- `:led2` → handler constant `kFwHwLed2`
- `:led3` → handler constant `kFwHwLed3`
