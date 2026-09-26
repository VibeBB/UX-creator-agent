# Ruby idioms for the ux-dsl library

The DSL (`ruby/lib/ux_dsl.rb`) targets plain, stdlib-only Ruby — the kind
a Rubyist writes, not a framework's magic.

- `# frozen_string_literal: true` first line of every file.
- Blocks + `instance_eval` for nesting (`journey do`, `statechart do`);
  keyword arguments everywhere (`layer:`, `importance:`).
- `Struct` value objects for records; `Data`/`pattern matching` allowed
  but not required.
- Symbols for ids, `%w[...]` for word lists, `each_with_object` for
  collection, trailing commas on multi-line literals.
- **No `method_missing`**, no monkey-patching, no external gems — the DSL
  only builds the contract hash; judgement lives in the Python gates.
- `ruby -w` warning-clean; `rubocop` (`ruby/.rubocop.yml`, Ruby 4.0
  target); `mrbc -c` validates snippets destined for mruby firmware.

The runner `ruby/bin/ux-dsl` evals the file in a clean binding and prints
`JSON.pretty_generate(design.to_h)` — byte-identical to the committed
`examples/smart-kettle/smart-kettle.ux.json` (asserted by
`scripts/check_ruby_dsl.py` and `ruby/test/ux_dsl_test.rb`).
