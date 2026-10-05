from __future__ import annotations

import ast
import json
from pathlib import Path

from ux_creator.mcp_server import tool_specs

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _cli_commands() -> set[str]:
    source = ast.parse((ROOT / "src/ux_creator/cli.py").read_text(encoding="utf-8"))
    return {
        call.args[0].value
        for call in ast.walk(source)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "add_parser"
        and call.args
        and isinstance(call.args[0], ast.Constant)
        and isinstance(call.args[0].value, str)
    }


def _missing(document: str, names: set[str]) -> list[str]:
    return sorted(name for name in names if f"`{name}`" not in document)


def test_docs_cover_current_plugin_and_tool_inventory() -> None:
    agents = {path.stem for path in (ROOT / "plugins/ux/agents").glob("*.md")}
    skills = {path.parent.name for path in (ROOT / "plugins/ux/skills").glob("*/SKILL.md")}
    plugin_commands = {path.stem for path in (ROOT / "plugins/ux/commands").glob("*.md")}
    hooks = json.loads((ROOT / "plugins/ux/hooks/hooks.json").read_text(encoding="utf-8"))
    hook_names = {
        hook["name"]
        for event_groups in hooks.values()
        for group in event_groups
        for hook in group["hooks"]
    }
    hook_scripts = {path.name for path in (ROOT / "plugins/ux/hooks/scripts").glob("*.py")}
    mcp_tools = {tool.name for tool in tool_specs()}
    cli = _cli_commands()

    inventories = {
        "agents.md": (agents, (DOCS / "agents.md").read_text(encoding="utf-8")),
        "skills.md": (skills, (DOCS / "skills.md").read_text(encoding="utf-8")),
        "commands.md": (
            cli | plugin_commands,
            (DOCS / "commands.md").read_text(encoding="utf-8"),
        ),
        "hooks.md": (
            hook_names | hook_scripts,
            (DOCS / "hooks.md").read_text(encoding="utf-8"),
        ),
        "mcp.md": (mcp_tools, (DOCS / "mcp.md").read_text(encoding="utf-8")),
    }
    missing = {
        document: absent
        for document, (names, content) in inventories.items()
        if (absent := _missing(content, names))
    }
    assert not missing, f"documentation omits current inventory: {missing}"


def test_readme_has_english_before_japanese() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# UX-creator-agent")
    assert readme.index("## 日本語") > readme.index("## Documentation")
