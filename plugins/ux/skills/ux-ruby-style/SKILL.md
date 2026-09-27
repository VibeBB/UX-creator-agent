---
name: ux-ruby-style
description: Idiomatic Ruby authoring with the ux-dsl library — DSL reference and style rules (blocks, keyword args, frozen string literal, no method_missing).
version: 0.1.0
license: BSD-3-Clause
triggers:
  - ruby dsl
  - ux.rb
  - ux-dsl
  - ruby style
  - Ruby
---

# Ruby DSL reference

Author contracts as `*.ux.rb` and compile with
`python -m ux_creator from-ruby file.ux.rb --out <project>.ux.json`
(or `ruby ruby/bin/ux-dsl file.ux.rb` for raw JSON).

```ruby
UX.design "kettle" do
  persona :busy_parent, goals: ["hot water fast"], context: "morning rush"
  job :boil, functional: "boil 500ml in <3min",
      emotional: "confidence it won't overflow",
      social: "kitchen looks tidy", importance: 9, satisfaction: 4
  journey :morning do
    stage :fill, touchpoints: %w[lid handle], emotion: 3
    stage :boil, touchpoints: %w[button led], emotion: 4,
          surfaces: %w[hardware_button]
  end
  statechart :power do
    state :idle, initial: true
    state :heating
    on :idle, :press, to: :heating
    on :heating, :boiled, to: :idle
  end
  surface :hardware_button, layer: :hardware
  core_experience "one press, walk away"
  qcd quality: :high, cost: :medium, delivery: :fast
end
```

## DSL methods

`design` → `persona, job, journey{stage}, service_blueprint,
statechart{state, on}, surface, core_experience, implementation_spec,
qcd, import`.

- `surface` layer ∈ hardware, mechanism, industrial_design, circuit,
  firmware, cloud_backend, web_ui, smartphone_app, pc_app
- `qcd` quality/cost ∈ low|medium|high; delivery ∈ slow|normal|fast
- `import system:, path:, sha256:` records sibling provenance

## Style rules (enforced by rubocop in the image)

- `# frozen_string_literal: true` first line, every file.
- Plain stdlib Ruby only: blocks, keyword args, `Struct`, pattern
  matching allowed. No `method_missing`, no external gems.
- `%w[...]` for word lists, symbols for ids, trailing commas on
  multi-line literals.
- `ruby -w` must be warning-clean; `rubocop` (config `ruby/.rubocop.yml`)
  must pass; `mrbc -c` checks snippets headed for embedded firmware.
