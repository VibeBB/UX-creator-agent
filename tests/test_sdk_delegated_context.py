"""Exercise SDK task creation and real SessionStart shell execution without an LLM call."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path

import pytest

pytest.importorskip("openhands.sdk")

from openhands.sdk import LLM, Agent
from openhands.sdk.conversation.impl.local_conversation import LocalConversation
from openhands.sdk.hooks.config import HookConfig
from openhands.sdk.plugin import Plugin
from openhands.sdk.subagent.registry import register_plugin_agents
from openhands.sdk.tool.builtins import VisionInspectTool
from openhands.sdk.tool.registry import (
    list_registered_tools,
    register_tool,  # pyright: ignore[reportUnknownVariableType]
)
from openhands.tools.glob import GlobTool
from openhands.tools.grep import GrepTool
from openhands.tools.preset.default import register_default_tools
from openhands.tools.task.manager import TaskManager
from pydantic import SecretStr

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugins/ux"


@pytest.mark.parametrize("name", ["ux-review", "ux-blind-review"])
def test_sdk_delegate_receives_only_own_record_context(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UX_PLUGIN_ROOT", str(PLUGIN_DIR))
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("OPENHANDS_SESSION_ID", raising=False)
    register_default_tools(enable_browser=False)
    for tool_name, factory in {
        "glob": GlobTool,
        "grep": GrepTool,
        "VisionInspectTool": VisionInspectTool,
    }.items():
        if tool_name not in list_registered_tools():
            register_tool(tool_name, factory)
    plugin = Plugin.load(PLUGIN_DIR)
    definition = next(agent for agent in plugin.agents if agent.name == name)
    # Keep the shipped hooks; provider profiles and MCP startup are outside this check.
    definition = definition.model_copy(update={"model": "inherit", "mcp_config": {}})
    register_plugin_agents([definition], tmp_path)
    root_hooks = HookConfig.model_validate(
        {
            "session_start": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                "printf '%s' '{\"additionalContext\":\"PARENT_RECALL_SENTINEL\"}'"
                            ),
                        }
                    ]
                }
            ]
        }
    )
    llm = LLM(model="gpt-4o", api_key=SecretStr("unused"))
    with closing(
        LocalConversation(
            agent=Agent(llm=llm, tools=[]),
            workspace=tmp_path,
            hook_config=root_hooks,
            visualizer=None,
        )
    ) as parent:
        parent._ensure_plugins_loaded()
        assert parent._hook_processor is not None
        assert parent._hook_processor._pending_additional_context == ["PARENT_RECALL_SENTINEL"]
        manager = TaskManager()
        manager.attach_parent(parent)
        task = manager._create_task(subagent_type=name, description="Check native startup")
        assert task.conversation is not None
        with closing(task.conversation) as child:
            child._ensure_plugins_loaded()
            assert child.state.id != parent.state.id
            assert child._hook_processor is not None
            context = "\n".join(child._hook_processor._pending_additional_context)
            assert f'session_id="{child.state.id}"' in context
            assert str(parent.state.id) not in context
            assert "PARENT_RECALL_SENTINEL" not in context
            marker = tmp_path / "observations/ux/.sessions" / f"{child.state.id}.json"
            assert (
                json.loads(marker.read_text(encoding="utf-8"))["scope_origin"] == "record-context"
            )
