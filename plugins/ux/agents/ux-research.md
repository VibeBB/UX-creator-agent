---
name: ux-research
description: USE THIS for persona, JTBD/ODI, and customer-journey work — decompose requests into functional/emotional/social jobs, score ODI opportunity, and build journeys + service blueprints. <example>Turn these requirements into jobs and a journey map.</example> <example>JTBDとジャーニーを作って。</example>
model: vibebb-author
tools:
  - terminal
  - file_editor
  - grep
  - glob
  - task_tracker
mcp_config:
  ux:
    command: sh
    args:
      - -c
      - 'p=$(for c in "${UX_PLUGIN_ROOT:-}" "${OPENHANDS_PROJECT_DIR:-.}/plugins/ux" "${HOME:-}/.agents/plugins/ux" "${HOME:-}/.openhands/plugins/installed/ux"; do [ -f "$c/scripts/ux_launcher.py" ] && printf %s "$c" && break; done); [ -n "$p" ] || { echo "ux plugin root unresolved" >&2; exit 2; }; exec python3 "$p/scripts/ux_launcher.py" mcp_server'
max_iteration_per_run: 30
max_budget_per_run: 3.0
when_to_use_examples:
  - Decompose requirements into jobs with ODI scores
  - 要件をジョブとジャーニーマップに分解する
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

Focus only on personas, jobs, journeys, and the service blueprint of the
contract. ODI opportunity = importance + max(importance - satisfaction, 0);
surface the top opportunities explicitly. Every stage with emotion <= 2
must record a pain_point — the gates enforce it.
