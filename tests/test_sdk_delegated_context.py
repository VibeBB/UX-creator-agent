"""Exercise SDK task creation and real SessionStart shell execution without an LLM call."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import base64
import json
from contextlib import closing
from datetime import UTC, datetime
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
    liaison = tmp_path / "liaison"
    liaison.mkdir()
    (liaison / "pending.bard-song.json").write_text(
        json.dumps(
            {
                "kind": "bard_song_delivery",
                "schema_version": 1,
                "id": "pending",
                "system": "bard",
                "to": "ux",
                "title": "Pending song",
                "verse": "A blind reader follows the lines while a caller gathers the signs.",
                "song": {"path": "song.md", "sha256": "a" * 64},
                "impression_refs": [{"system": "ux", "event_id": "b" * 64}],
                "reason": "The caller owns this song receipt while the reviewer stays blind.",
                "created_at": datetime.now(UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )
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
            ],
            "stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                f'python3 "{PLUGIN_DIR}/hooks/scripts/require_records.py" stop'
                            ),
                        }
                    ]
                }
            ],
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
        should_stop, feedback = parent._hook_processor.run_stop()
        assert not should_stop
        assert feedback is not None and "record a song receipt" in feedback
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
            image = tmp_path / "delegated-image.png"
            image.write_bytes(b"fixture-image-bytes")
            image_results = child._hook_processor.hook_manager.run_post_tool_use(
                "file_editor",
                {"command": "view", "path": str(image)},
                {
                    "content": [
                        {
                            "type": "image",
                            "image_urls": [
                                "data:image/png;base64,"
                                + base64.b64encode(image.read_bytes()).decode("ascii")
                            ],
                        }
                    ]
                },
            )
            assert image_results and all(result.success for result in image_results)
            image_log = tmp_path / "observations/ux/image-observations.jsonl"
            delivered = json.loads(image_log.read_text(encoding="utf-8"))
            assert delivered["session_id"] == str(child.state.id)
            assert delivered["image_path"] == str(image)
            results = child._hook_processor.hook_manager.run_post_tool_use(
                "inspect_image_with_vision",
                {"image_index": 0, "question": "Read the image"},
                {"answer": "Independent findings", "profile_name": "vision", "model": "test"},
            )
            assert results and all(result.success for result in results)
            events_path = tmp_path / "observations/ux/vision-tool-events.jsonl"
            event = json.loads(events_path.read_text(encoding="utf-8"))
            assert event["session_id"] == str(child.state.id)
            assert event["source_image_status"] == "unknown"
            if name == "ux-blind-review":
                allowed, results = child._hook_processor.hook_manager.run_pre_tool_use(
                    "file_editor",
                    {"command": "view", "path": str(liaison / "pending.bard-song.json")},
                )
                assert not allowed and any(result.blocked for result in results)
            should_stop, feedback = child._hook_processor.run_stop()
            if name == "ux-blind-review":
                assert should_stop and feedback is None
            else:
                assert not should_stop
                assert feedback is not None and "record a song receipt" in feedback
