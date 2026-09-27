---
description: QCD-triage a .ux-proposals.json into ux-request.json change requests for sibling agents.
argument-hint: --contract <contract.ux.json> --proposals <name>.ux-proposals.json --out-dir <dir>
allowed-tools:
  - terminal
  - file_editor
---

Use `python -m ux_creator propose`. Each proposal is scored
deterministically: low-risk changes become ux-request.json files
immediately (`auto_send`), high-risk changes are held until the
rationale cites a job id (`needs_rationale`), and layers with no sibling
agent report `no_target`. Single requests can still be written directly
with `python -m ux_creator request`; high-risk requests must cite a job
id in the rationale.
