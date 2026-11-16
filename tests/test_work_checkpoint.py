"""Exercise evidence collection with synthetic SLP fixtures, never provider calls."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ux_creator import mcp_server
from ux_creator.cli import main
from ux_creator.contract import UXContract
from ux_creator.records import tree_sha256
from ux_creator.requests import build_request, write_request
from ux_creator.responses import ArtifactRef, GateVerdict, UXResponse
from ux_creator.work_checkpoint import work_checkpoint


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("OPENHANDS_SESSION_ID", raising=False)
    monkeypatch.delenv("OPENHANDS_CONVERSATION_ID", raising=False)
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    (tmp_path / "brief.json").write_text('{"requirement": "bounded work"}', encoding="utf-8")
    return tmp_path


def _call(root: Path, action: str, **fields: Any) -> dict[str, Any]:
    return work_checkpoint(
        {"action": action, "checkpoint_id": "run", "session_id": "coordinator", **fields}, root
    )


def _create(root: Path, **fields: Any) -> dict[str, Any]:
    return _call(
        root,
        "create",
        source_path="brief.json",
        steps=fields.pop(
            "steps", [{"id": "ux", "kind": "design", "output_contract": "design.ux.json"}]
        ),
        **fields,
    )


def _active(result: dict[str, Any]) -> dict[str, Any]:
    return next(step for step in result["steps"] if step["active"])


def _finish(
    root: Path, started: dict[str, Any], action: str = "collect", **fields: Any
) -> dict[str, Any]:
    step = _active(started)
    return _call(
        root,
        action,
        step_id=step["spec"]["id"],
        attempt_id=step["attempts"][-1]["id"],
        child_session_id=fields.pop("child_session_id", "child-" + step["spec"]["id"]),
        **fields,
    )


def _design(root: Path, contract_dict: dict[str, Any]) -> None:
    (root / "design.ux.json").write_text(json.dumps(contract_dict), encoding="utf-8")


def _request(root: Path, contract_dict: dict[str, Any], name: str = "cues", **fields: Any) -> None:
    request = build_request(
        UXContract.model_validate(contract_dict),
        id=name,
        target_agent=fields.pop("target", "bard"),
        stage="design",
        risk="low",
        purpose="Exercise the bounded evidence collection protocol",
        rationale="",
        requested_changes=["Produce the requested synthetic artifact"],
        inputs=["design.ux.json"],
        expected_deliverables=[name + ".txt"],
        acceptance=["Artifact must match its response SHA"],
        workspace=root,
        depends_on=fields.pop("depends_on", []),
        now=datetime(2025, 1, 1, tzinfo=UTC),
        **fields,
    )
    write_request(request, root / "liaison")


def _response(root: Path, name: str = "cues", **fields: Any) -> Path:
    artifact = root / (name + ".txt")
    artifact.write_text("Synthetic protocol fixture, not product evidence", encoding="utf-8")
    response = UXResponse(
        request=name,
        responder=fields.pop("responder", "bard"),
        status=fields.pop("status", "done"),
        reason="Synthetic fixture exercises intact evidence collection.",
        input_hashes={"design.ux.json": tree_sha256(root / "design.ux.json")},
        artifacts=[ArtifactRef(path=artifact.name, sha256=tree_sha256(artifact))],
        gate_verdicts=fields.pop("gate_verdicts", [GateVerdict(gate="fixture", verdict="pass")]),
        responded_at="2025-01-01T00:00:00Z",
        **fields,
    )
    path = root / "liaison" / (name + ".ux-response.json")
    path.write_text(response.model_dump_json(), encoding="utf-8")
    return path


def _sister(kind: str = "liaison", **fields: Any) -> dict[str, Any]:
    return {
        "id": "cues",
        "kind": kind,
        "target_agent": "bard",
        "request_path": "liaison/cues.ux-request.json",
        **fields,
    }


def test_design_liaison_domain_reuse_and_native_briefs(
    workspace: Path, contract_dict: dict[str, Any]
) -> None:
    _create(
        workspace,
        steps=[
            {"id": "ux", "kind": "design", "output_contract": "design.ux.json"},
            _sister(depends_on=["ux"]),
            _sister(
                "domain",
                id="build",
                target_agent="firmware",
                request_path="liaison/build.ux-request.json",
                depends_on=["cues"],
            ),
        ],
    )
    started = _call(workspace, "start")
    assert started["delegate"]["subagent_type"] == "ux-creator"
    assert "resume" not in started["delegate"]
    _design(workspace, contract_dict)
    assert _finish(workspace, started)["remaining_steps"] == ["cues", "build"]
    _request(workspace, contract_dict)
    started = _call(workspace, "start")
    assert started["delegate"]["subagent_type"] == "bard"
    assert "liaison/cues.ux-request.json" in started["delegate"]["prompt"]
    _response(workspace, status="in_progress")
    with pytest.raises(ValueError, match="done"):
        _finish(workspace, started)
    _response(workspace)
    _finish(workspace, started)
    _request(workspace, contract_dict, "build", target="firmware", depends_on=["cues"])
    started = _call(workspace, "start")
    _response(workspace, "build", responder="firmware")
    result = _finish(workspace, started, reported_usage={"native_iterations": 3, "cost_usd": 0.01})
    assert result["status"] == "collected"
    assert result["attempts_consumed"] == 3
    assert result["remaining_steps"] == []
    assert result["acceptance"] == result["workflow_completion"] == "unknown"
    assert result["native_execution"] == "unknown"
    assert _call(workspace, "start")["delegate"] is None
    assert _call(workspace, "status")["attempts_consumed"] == 3


@pytest.mark.parametrize(
    "reason", ["provider 429 Retry-After", "timeout", "budget exhausted", "cancelled"]
)
def test_two_fresh_attempts_persist_gaps_and_recover_without_a_third_child(
    workspace: Path, contract_dict: dict[str, Any], reason: str
) -> None:
    _create(workspace)
    starts: list[dict[str, Any]] = []
    result: dict[str, Any] = {}
    for index in range(2):
        started = _call(workspace, "start")
        assert started["status"] == "active" and not started["gaps"]
        starts.append(started)
        result = _finish(
            workspace, started, "pause", child_session_id=f"fresh-{index}", reason=reason
        )
    assert result["status"] == "blocked"
    assert _call(workspace, "start")["delegate"] is None
    assert starts[0]["steps"][0]["attempts"][0]["id"] != starts[1]["steps"][0]["attempts"][1]["id"]
    _design(workspace, contract_dict)
    recovered = _finish(workspace, starts[-1], child_session_id="fresh-1")
    assert recovered["status"] == "collected"
    assert recovered["attempts_consumed"] == 2
    assert [attempt["gap"] for attempt in recovered["steps"][0]["attempts"]] == [reason, reason]


def test_run_budget_is_immutable_and_shared_between_steps(
    workspace: Path, contract_dict: dict[str, Any]
) -> None:
    _create(
        workspace,
        attempt_budget=1,
        steps=[
            {"id": "a", "kind": "design", "output_contract": "a.ux.json"},
            {"id": "b", "kind": "design", "output_contract": "b.ux.json"},
        ],
    )
    started = _call(workspace, "start")
    (workspace / "a.ux.json").write_text(json.dumps(contract_dict), encoding="utf-8")
    assert _finish(workspace, started)["status"] == "blocked"
    assert _call(workspace, "start")["delegate"] is None
    with pytest.raises(ValueError, match="only create"):
        _call(workspace, "start", attempt_budget=100)
    with pytest.raises(ValueError, match="already exists"):
        _create(workspace)


def test_active_reservation_survives_and_rejects_stale_attempts_or_reused_children(
    workspace: Path,
) -> None:
    _create(workspace)
    first = _call(workspace, "start")
    with pytest.raises(ValueError, match="active"):
        _call(workspace, "start")
    _finish(workspace, first, "pause", child_session_id="old-child", reason="interruption")
    second = _call(workspace, "start")
    with pytest.raises(ValueError, match="last reserved"):
        _finish(workspace, first)
    for child in ("old-child", "coordinator"):
        with pytest.raises(ValueError, match="fresh child"):
            _finish(workspace, second, child_session_id=child)


@pytest.mark.parametrize("damage", ["source", "contract", "input", "response", "artifact"])
def test_changed_completed_evidence_blocks_reuse_without_rewriting_status(
    workspace: Path, contract_dict: dict[str, Any], damage: str
) -> None:
    _design(workspace, contract_dict)
    _request(workspace, contract_dict)
    (workspace / "extra.txt").write_text("pinned input", encoding="utf-8")
    _create(workspace, steps=[_sister("domain", inputs=["extra.txt"])])
    started = _call(workspace, "start")
    response = _response(workspace)
    _finish(workspace, started)
    damaged = {
        "source": workspace / "brief.json",
        "contract": workspace / "design.ux.json",
        "input": workspace / "extra.txt",
        "response": response,
        "artifact": workspace / "cues.txt",
    }[damage]
    damaged.write_text("changed", encoding="utf-8")
    checkpoint = workspace / "observations/ux/work-checkpoints/run.json"
    before = checkpoint.read_bytes(), checkpoint.stat().st_mtime_ns
    result = _call(workspace, "status")
    assert result["status"] == "blocked" and result["gaps"]
    assert _call(workspace, "start")["delegate"] is None
    assert (checkpoint.read_bytes(), checkpoint.stat().st_mtime_ns) == before


@pytest.mark.parametrize(
    "status", ["accepted", "in_progress", "needs_info", "deferred", "rejected"]
)
def test_incomplete_responses_never_complete_a_step(
    workspace: Path, contract_dict: dict[str, Any], status: str
) -> None:
    _design(workspace, contract_dict)
    _request(workspace, contract_dict)
    _create(workspace, steps=[_sister()])
    started = _call(workspace, "start")
    _response(workspace, status=status)
    with pytest.raises(ValueError, match="done"):
        _finish(workspace, started)
    assert _call(workspace, "status")["status"] == "active"


def test_domain_requires_gate_evidence_and_current_request_target(
    workspace: Path, contract_dict: dict[str, Any]
) -> None:
    _design(workspace, contract_dict)
    _request(workspace, contract_dict)
    with pytest.raises(ValueError, match="target"):
        _create(workspace, steps=[_sister(target_agent="firmware")])
    _create(workspace, steps=[_sister("domain")])
    started = _call(workspace, "start")
    _response(workspace, gate_verdicts=[])
    with pytest.raises(ValueError, match="gate verdicts"):
        _finish(workspace, started)


def test_design_is_validated_by_current_deterministic_gates(
    workspace: Path, contract_dict: dict[str, Any]
) -> None:
    _create(workspace)
    started = _call(workspace, "start")
    contract_dict["statecharts"][0]["transitions"][0]["to"] = "missing-state"
    _design(workspace, contract_dict)
    with pytest.raises(ValueError, match="design gates"):
        _finish(workspace, started)


@pytest.mark.parametrize("case", ["session", "seal", "outside", "symlink", "cycle"])
def test_identity_integrity_and_workspace_boundaries(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    if case == "outside":
        with pytest.raises(ValueError, match="outside"):
            _create(
                workspace,
                steps=[{"id": "ux", "kind": "design", "output_contract": "../outside.json"}],
            )
        return
    if case == "symlink":
        (workspace / "link").symlink_to(workspace, target_is_directory=True)
        with pytest.raises(ValueError, match="symlink"):
            _create(
                workspace,
                steps=[{"id": "ux", "kind": "design", "output_contract": "link/design.json"}],
            )
        return
    if case == "cycle":
        with pytest.raises(ValueError, match="dependencies"):
            _create(
                workspace,
                steps=[
                    {
                        "id": "ux",
                        "kind": "design",
                        "output_contract": "design.json",
                        "depends_on": ["ux"],
                    }
                ],
            )
        return
    _create(workspace)
    if case == "session":
        monkeypatch.setenv("OPENHANDS_SESSION_ID", "foreign")
        with pytest.raises(ValueError, match="OPENHANDS_SESSION_ID"):
            _call(workspace, "status")
    else:
        path = workspace / "observations/ux/work-checkpoints/run.json"
        body = json.loads(path.read_text(encoding="utf-8"))
        body["attempt_budget"] = 100
        path.write_text(json.dumps(body), encoding="utf-8")
        with pytest.raises(ValueError, match="integrity"):
            _call(workspace, "status")


def test_cli_and_mcp_expose_the_same_collector_and_side_effect_hints(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _create(workspace)
    request = workspace / "status.json"
    request.write_text(
        json.dumps({"action": "status", "checkpoint_id": "run", "session_id": "coordinator"}),
        encoding="utf-8",
    )
    assert main(["work-checkpoint", "--json", str(request)]) == 1
    assert json.loads(capsys.readouterr().out)["acceptance"] == "unknown"
    result = asyncio.run(
        mcp_server.dispatch_tool(
            "ux_work_checkpoint", json.loads(request.read_text(encoding="utf-8"))
        )
    )
    assert isinstance(result, dict) and result["status"] == "pending"
    tool = next(tool for tool in mcp_server.tool_specs() if tool.name == "ux_work_checkpoint")
    assert tool.annotations is not None
    assert tool.annotations.read_only_hint is False
    assert tool.annotations.idempotent_hint is False


def test_two_coordinators_cannot_reserve_the_same_step(workspace: Path) -> None:
    _create(workspace)
    request = workspace / "start.json"
    request.write_text(
        json.dumps({"action": "start", "checkpoint_id": "run", "session_id": "coordinator"}),
        encoding="utf-8",
    )
    children = [
        subprocess.Popen(
            [sys.executable, "-m", "ux_creator", "work-checkpoint", "--json", str(request)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]
    results = [json.loads(child.communicate(timeout=30)[0]) for child in children]
    assert all(child.returncode == 1 for child in children)
    assert sum(result.get("status") == "active" for result in results) == 1
    assert any("active" in result.get("detail", "") for result in results)
    assert _call(workspace, "status")["attempts_consumed"] == 1


def test_failed_atomic_replace_leaves_the_previous_checkpoint(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _create(workspace)
    path = workspace / "observations/ux/work-checkpoints/run.json"
    before = path.read_bytes()

    def fail(_self: Path, _target: Path) -> Path:
        raise OSError("synthetic interrupted replace")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail)
        with pytest.raises(OSError, match="interrupted replace"):
            _call(workspace, "start")
    assert path.read_bytes() == before
    assert sorted(item.name for item in path.parent.iterdir()) == ["run.json", "run.lock"]
    assert _call(workspace, "start")["attempts_consumed"] == 1


@pytest.mark.parametrize("budget", [True, "2", 0, 101])
def test_attempt_budget_is_a_strict_bounded_integer(workspace: Path, budget: object) -> None:
    with pytest.raises(ValueError):
        _create(workspace, attempt_budget=budget)
