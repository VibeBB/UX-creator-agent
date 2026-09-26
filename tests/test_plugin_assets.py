"""Plugin asset consistency checks for plugins/ux."""

from __future__ import annotations

import json
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "ux"
REQUIRED_FRONTMATTER = ("name:", "description:")

EXPECTED_AGENTS = {"ux-creator", "ux-research", "ux-statechart", "ux-review", "ux-liaison"}
EXPECTED_COMMANDS = {"doctor", "discover", "journey", "statechart", "review", "propose"}
EXPECTED_SKILLS = {
    "ux-workflow",
    "ux-persona",
    "ux-theory-lenses",
    "ux-jtbd",
    "ux-diagrams",
    "ux-ruby-style",
    "ux-sibling-cooperation",
}


def test_plugin_manifest() -> None:
    data = json.loads((PLUGIN_ROOT / ".plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert data["name"] == "ux"
    assert data["license"] == "BSD-3-Clause"
    assert data["version"]
    assert data["entry_command"] == "doctor"


def test_mcp_config() -> None:
    data = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    ux = data["mcpServers"]["ux"]
    assert ux["command"] == "sh"
    joined = " ".join(ux["args"])
    assert "ux_launcher.py" in joined
    assert "mcp_server" in joined


def test_hooks_config() -> None:
    data = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert set(data) >= {
        "session_start",
        "user_prompt_submit",
        "pre_tool_use",
        "stop",
        "post_tool_use",
    }
    for groups in data.values():
        for group in groups:
            for hook in group["hooks"]:
                assert hook["type"] == "command"
                assert hook["command"]


def test_skill_frontmatter() -> None:
    skills = sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
    assert {s.parent.name for s in skills} == EXPECTED_SKILLS
    for skill in skills:
        head = skill.read_text(encoding="utf-8")[:600]
        for marker in REQUIRED_FRONTMATTER:
            assert marker in head, f"{skill} missing {marker}"


def test_agent_frontmatter() -> None:
    agents = sorted((PLUGIN_ROOT / "agents").glob("*.md"))
    assert {a.stem for a in agents} == EXPECTED_AGENTS
    for agent in agents:
        head = agent.read_text(encoding="utf-8")
        for marker in (*REQUIRED_FRONTMATTER, "model:", "tools:", "permission_mode:"):
            assert marker in head, f"{agent} missing {marker}"


def test_command_frontmatter() -> None:
    commands = sorted((PLUGIN_ROOT / "commands").glob("*.md"))
    assert {c.stem for c in commands} == EXPECTED_COMMANDS
    for command in commands:
        head = command.read_text(encoding="utf-8")[:400]
        assert "description:" in head
        assert "allowed-tools:" in head
