"""Exercise shipped native task limits with synthetic steps, without provider calls."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path

import pytest

pytest.importorskip("openhands.sdk")

from openhands.sdk import LLM, Agent
from openhands.sdk.conversation.impl.local_conversation import LocalConversation
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
from openhands.tools.task.definition import TaskAction
from openhands.tools.task.impl import TaskExecutor
from openhands.tools.task.manager import TaskManager
from pydantic import SecretStr

from ux_creator.review_checkpoint import review_checkpoint

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/ux"


@pytest.mark.parametrize("role", ["ux-review", "ux-blind-review"])
@pytest.mark.parametrize("condition", ["iterations", "budget", "pause", "timeout"])
def test_native_fresh_task_limits_and_failure_delivery(
    role: str, condition: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UX_PLUGIN_ROOT", str(PLUGIN))
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
    definition = next(agent for agent in Plugin.load(PLUGIN).agents if agent.name == role)
    # Keep shipped limits/hooks; profile resolution and MCP startup are separate checks.
    register_plugin_agents(
        [definition.model_copy(update={"model": "inherit", "mcp_config": {}})], tmp_path
    )
    calls: dict[str, int] = {}

    def synthetic_step(self: Agent, conversation: LocalConversation, **_unused: object) -> None:
        child_id = str(conversation.state.id)
        calls[child_id] = calls.get(child_id, 0) + 1
        assert conversation.max_iteration_per_run == 20
        assert conversation.max_budget_per_run == 1.5
        if calls[child_id] == 1:
            assert conversation.conversation_stats.get_combined_metrics().accumulated_cost == 0
        assert conversation._hook_processor is not None
        # run() already consumed SessionStart context into the child conversation.
        marker = tmp_path / "observations/ux/.sessions" / f"{child_id}.json"
        assert json.loads(marker.read_text(encoding="utf-8"))["scope_origin"] == "record-context"
        if role == "ux-blind-review":
            for tool, payload in [
                ("ux_review_checkpoint", {"action": "status"}),
                ("ux_ux_review_checkpoint", {"action": "status"}),
                (
                    "terminal",
                    {"command": "python -m ux_creator review-checkpoint --json input.json"},
                ),
            ]:
                allowed, _ = conversation._hook_processor.hook_manager.run_pre_tool_use(
                    tool, payload
                )
                assert not allowed
        if condition == "budget":
            # Synthetic accounting crosses the real SDK budget gate; no spend occurs.
            self.llm.metrics.add_cost(1.6)
            assert conversation.conversation_stats.get_combined_metrics().accumulated_cost == 1.6
        elif condition == "pause":
            conversation.pause()
        elif condition == "timeout":
            raise TimeoutError("synthetic provider timeout, no network request")

    monkeypatch.setattr(Agent, "step", synthetic_step)
    with (
        closing(
            LocalConversation(
                agent=Agent(llm=LLM(model="gpt-4o", api_key=SecretStr("unused")), tools=[]),
                workspace=tmp_path,
                visualizer=None,
            )
        ) as parent,
        closing(TaskExecutor(TaskManager())) as executor,
    ):
        parent_id = str(parent.state.id)
        (tmp_path / "contract.json").write_text("{}", encoding="utf-8")
        (tmp_path / "image.png").write_bytes(b"synthetic image, never perceived")
        common = {"checkpoint_id": "native", "session_id": parent_id}
        review_checkpoint(
            {
                **common,
                "action": "create",
                "contract_path": "contract.json",
                "sources": [{"image_path": "image.png", "checklist": "statechart"}],
            },
            tmp_path,
        )
        for attempt in range(1, 3):
            reserved = review_checkpoint({**common, "action": "start"}, tmp_path)
            # Native failure propagation is identical for both shipped reviewer definitions.
            action = TaskAction(subagent_type=role, prompt="Inspect exactly one synthetic source.")
            assert action.resume is None
            result = executor(action, conversation=parent)
            assert result.is_error and result.status == "error"
            detail = result.text
            if condition == "iterations":
                assert "maximum iterations limit (20)" in detail
            elif condition == "budget":
                assert "maximum budget limit ($1.5000)" in detail
            elif condition == "pause":
                assert "paused" in detail.lower()
            else:
                assert "synthetic provider timeout" in detail
            assert reserved["status"] == "running"
            paused = review_checkpoint({**common, "action": "pause", "reason": detail}, tmp_path)
            pairs = paused["pairs"]
            assert isinstance(pairs, list)
            pair = pairs[0]
            assert isinstance(pair, dict)
            assert pair["attempts"] == attempt
            gaps = pair["attempt_gaps"]
            assert isinstance(gaps, list) and len(gaps) == attempt
        assert len(calls) == 2 and parent_id not in calls
        assert set(calls.values()) == {20 if condition == "iterations" else 1}
        with pytest.raises(ValueError, match="no eligible pair"):
            review_checkpoint({**common, "action": "start"}, tmp_path)
