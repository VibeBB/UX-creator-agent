from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, cast

import pytest
from mcp import types

from ux_creator import mcp_server
from ux_creator.sisters import SISTERS


async def _call_tool(name: str, arguments: dict[str, Any]) -> object:
    return await mcp_server.call_tool(name, arguments)


def _payload(result: types.CallToolResult) -> dict[str, Any]:
    assert result.content and isinstance(result.content[0], types.TextContent)
    return json.loads(result.content[0].text)


def _dispatch_payload(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = asyncio.run(mcp_server.dispatch_tool(name, arguments))
    assert isinstance(result, dict)
    return result


def test_unknown_tool_is_a_transport_error() -> None:
    result = asyncio.run(_call_tool("ux_unknown", {}))
    assert isinstance(result, types.CallToolResult)
    assert result.isError is True
    assert _payload(result) == {"verdict": "fail", "detail": "unknown tool ux_unknown"}


def test_handler_exception_is_a_typed_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(_name: str, _arguments: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("handler failed")

    monkeypatch.setattr(mcp_server, "dispatch_tool", fail)
    result = asyncio.run(_call_tool("ux_doctor", {}))
    assert isinstance(result, types.CallToolResult)
    assert result.isError is True
    payload = _payload(result)
    assert payload["detail"] == "ux_doctor error: handler failed"
    assert payload["error_type"] == "RuntimeError"


def test_gate_validation_failure_is_not_a_transport_error() -> None:
    result = asyncio.run(_call_tool("ux_validate_contract", {"contract": {}}))
    assert isinstance(result, list)
    content = cast(list[types.ContentBlock], result)
    assert content and isinstance(content[0], types.TextContent)
    payload = json.loads(content[0].text)
    assert payload["verdict"] == "fail"
    assert payload["stage"] == "validate"


def test_path_escape_is_a_transport_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    result = asyncio.run(_call_tool("ux_render", {"dir": "../outside"}))
    assert isinstance(result, types.CallToolResult)
    assert result.isError is True
    payload = _payload(result)
    assert payload["error_type"] == "ValueError"
    assert "outside the workspace" in payload["detail"]


def test_record_tools_are_declared_append_only() -> None:
    tools = {tool.name: tool for tool in mcp_server.tool_specs()}
    append_tools = {
        "ux_record_decision",
        "ux_record_impression",
        "ux_record_vision_review",
    }
    assert append_tools | {"ux_records_status"} <= tools.keys()
    for name in append_tools:
        annotations = tools[name].annotations
        assert annotations is not None
        assert annotations.readOnlyHint is False
        assert annotations.destructiveHint is False
        assert annotations.idempotentHint is False
    status_annotations = tools["ux_records_status"].annotations
    assert status_annotations is not None
    assert status_annotations.readOnlyHint is True
    delegate_annotations = tools["ux_delegate"].annotations
    assert delegate_annotations is not None
    assert delegate_annotations.readOnlyHint is True
    assert delegate_annotations.destructiveHint is False
    render_annotations = tools["ux_render"].annotations
    assert render_annotations is not None
    assert render_annotations.readOnlyHint is False
    assert render_annotations.destructiveHint is False
    assert render_annotations.idempotentHint is True


def test_mcp_tools_have_explicit_descriptions() -> None:
    for tool in mcp_server.tool_specs():
        assert tool.description
        assert tool.description.strip() != tool.name.replace("_", " ")


def test_mcp_request_and_delegate_round_trip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    contract_path = tmp_path / "smart-kettle.ux.json"
    contract_path.write_bytes(
        (
            Path(__file__).resolve().parents[1] / "examples/smart-kettle/smart-kettle.ux.json"
        ).read_bytes()
    )
    request = _dispatch_payload(
        "ux_request",
        {
            "contract_path": str(contract_path),
            "id": "circuit-request",
            "target_agent": "circuit",
            "stage": "design",
            "risk": "high",
            "purpose": "Coordinate the status LED hardware change",
            "rationale": "job boil requires a readable status LED",
            "requested_changes": ["review the status LED driver"],
            "expected_deliverables": ["updated circuit design"],
            "acceptance": ["status remains visible during keep warm"],
            "workspace": str(tmp_path),
            "liaison_dir": "liaison",
        },
    )
    assert request["verdict"] == "pass"
    delegated = _dispatch_payload(
        "ux_delegate",
        {
            "request_id": "circuit-request",
            "workspace": str(tmp_path),
            "liaison_dir": "liaison",
        },
    )
    assert delegated["verdict"] == "pass"
    assert delegated["delegate"]["subagent_type"] == SISTERS["circuit"].liaison_agent
    assert "task_tool_set" not in delegated["delegate"]
    assert SISTERS["circuit"].record_decision_tool in delegated["delegate"]["prompt"]
    assert SISTERS["circuit"].record_impression_tool in delegated["delegate"]["prompt"]
    assert "ux_record_" not in delegated["delegate"]["prompt"]


def test_records_status_mcp_tool_uses_current_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    payload = _dispatch_payload("ux_records_status", {})
    assert payload["records_dir"] == str(tmp_path / "observations" / "ux")
