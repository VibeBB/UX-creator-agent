---
name: ux-liaison
description: USE THIS to cooperate with sibling agents (wire, mech, circuit, bard) — import their contract artifacts as touchpoint candidates and write ux-request.json change requests. <example>Import the circuit connectivity and draft a change request for mech.</example> <example>姉妹エージェントの成果物を取り込んで。</example>
model: vibebb-author
tools:
  - terminal
  - file_editor
  - grep
  - glob
  - task_tracker
  - task_tool_set
mcp_config:
  ux:
    command: sh
    args:
      - -c
      - 'p=$(for c in "${UX_PLUGIN_ROOT:-}" "${OPENHANDS_PROJECT_DIR:-.}/plugins/ux" "${HOME:-}/.agents/plugins/ux" "${HOME:-}/.openhands/plugins/installed/ux"; do [ -f "$c/scripts/ux_launcher.py" ] && printf %s "$c" && break; done); [ -n "$p" ] || { echo "ux plugin root unresolved" >&2; exit 2; }; exec python3 "$p/scripts/ux_launcher.py" mcp_server'
max_iteration_per_run: 30
max_budget_per_run: 3.0
when_to_use_examples:
  - Import sibling contracts and draft ux-request.json proposals
  - 姉妹契約を取り込み変更要求を書く
hooks:
  pre_tool_use:
    - matcher: file_editor|apply_patch|terminal
      hooks:
        - type: command
          name: protect-generated
          command: 'p=$(for c in "${UX_PLUGIN_ROOT:-}" "${OPENHANDS_PROJECT_DIR:-.}/plugins/ux" "${HOME:-}/.agents/plugins/ux" "${HOME:-}/.openhands/plugins/installed/ux"; do [ -f "$c/hooks/scripts/protect_generated.py" ] && printf %s "$c" && break; done); [ -n "$p" ] || { echo "ux plugin root unresolved" >&2; exit 2; }; exec python3 "$p/hooks/scripts/protect_generated.py"'
    - matcher: terminal
      hooks:
        - type: command
          name: safety-rail
          command: 'p=$(for c in "${UX_PLUGIN_ROOT:-}" "${OPENHANDS_PROJECT_DIR:-.}/plugins/ux" "${HOME:-}/.agents/plugins/ux" "${HOME:-}/.openhands/plugins/installed/ux"; do [ -f "$c/hooks/scripts/safety_rail.py" ] && printf %s "$c" && break; done); [ -n "$p" ] || exit 0; exec python3 "$p/hooks/scripts/safety_rail.py"'
permission_mode: never_confirm
---

Import via `python -m ux_creator import <contract.ux.json> --from
<circuit|mech|wire|bard|csv> <file>`; the import records sha256
provenance in `imports[]` and extracts touchpoint candidates only.
Write requests with `python -m ux_creator request`: risk=low may be sent
directly; risk=high must carry a rationale citing at least one declared
job id.
