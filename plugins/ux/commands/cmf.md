---
description: Author the industrial-design / CMF block (form language, color, material, finish, marking).
argument-hint: <contract.ux.json>
allowed-tools:
  - terminal
  - file_editor
---

Follow the `ux-cmf` skill. Edit the contract's `cmf` block, cover every
`hardware` / `mechanism` / `industrial_design` surface with a part, then
run `python -m ux_creator gates <contract>` until the `cmf.*` checks pass
and `python -m ux_creator author` to regenerate `<name>.cmf.md`. Route
material or process changes that affect tooling to `mech` through
`ux-liaison` as high-risk requests.
