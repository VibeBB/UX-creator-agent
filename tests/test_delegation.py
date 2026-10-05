"""Deterministic task-tool delegation briefs for SLP v2 requests."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ux_creator.contract import load_contract
from ux_creator.delegation import delegation_brief
from ux_creator.records import sha256_file
from ux_creator.requests import UXRequest, build_request, write_request
from ux_creator.sisters import SISTERS

CONTRACT = Path(__file__).resolve().parents[1] / "examples/smart-kettle/smart-kettle.ux.json"


def _request(workspace: Path) -> UXRequest:
    return build_request(
        load_contract(CONTRACT),
        id="circuit-request",
        target_agent="circuit",
        stage="design",
        risk="high",
        purpose="Coordinate the status LED hardware change",
        rationale="job boil requires a readable status LED",
        requested_changes=["review the status LED driver"],
        inputs=[],
        expected_deliverables=["updated circuit design"],
        acceptance=["status remains visible during keep warm"],
        workspace=workspace,
        now=datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_delegation_brief_uses_registry_protocol(tmp_path: Path) -> None:
    request = _request(tmp_path)
    brief = delegation_brief(request, "liaison")
    sister = SISTERS["circuit"]
    assert brief["subagent_type"] == sister.liaison_agent
    assert brief["description"] == "circuit answer circuit-request"
    assert "`liaison/circuit-request.ux-request.json`" in brief["prompt"]
    assert sister.inbox_tool in brief["prompt"]
    assert sister.respond_tool in brief["prompt"]
    assert "Never hand-write or edit the response JSON" in brief["prompt"]
    assert sister.repo in brief["prompt"]


@pytest.mark.parametrize(
    "path",
    ["", "../outside", "requests/../outside", "/tmp/liaison", r"C:\liaison", r"requests\liaison"],
)
def test_delegation_brief_rejects_unsafe_liaison_paths(tmp_path: Path, path: str) -> None:
    with pytest.raises(ValueError, match="workspace-relative"):
        delegation_brief(_request(tmp_path), path)


def test_cli_delegate_loads_request_and_prints_task_brief(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    request = _request(tmp_path)
    write_request(request, tmp_path / "liaison")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ux_creator",
            "delegate",
            request.id,
            "--workspace",
            str(tmp_path),
            "--liaison-dir",
            "liaison",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["stage"] == "delegate"
    assert payload["delegate"]["subagent_type"] == SISTERS["circuit"].liaison_agent


def test_cli_request_writes_v2_hashes_and_explicitly_replaces(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    source = tmp_path / "input.txt"
    source.write_text("verified design input\n", encoding="utf-8")
    command = [
        sys.executable,
        "-m",
        "ux_creator",
        "request",
        str(CONTRACT),
        "--id",
        "circuit-request",
        "--target",
        "circuit",
        "--stage",
        "design",
        "--risk",
        "high",
        "--purpose",
        "Coordinate the status LED hardware change",
        "--rationale",
        "job boil supports a readable status LED",
        "--change",
        "review the status LED driver",
        "--input",
        "input.txt",
        "--deliverable",
        "updated circuit design",
        "--accept",
        "status remains visible during keep warm",
        "--workspace",
        str(tmp_path),
        "--liaison-dir",
        "liaison",
    ]
    first = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr + first.stdout
    first_payload = json.loads(first.stdout)
    assert first_payload["delegate"]["subagent_type"] == SISTERS["circuit"].liaison_agent
    request_path = Path(first_payload["request"])
    request_doc = json.loads(request_path.read_text(encoding="utf-8"))
    assert request_doc["schema_version"] == 2
    assert request_doc["inputs"] == [{"path": "input.txt", "sha256": sha256_file(source)}]
    replacement = command.copy()
    purpose_index = replacement.index("--purpose") + 1
    replacement[purpose_index] = "Coordinate the revised status LED hardware change"
    replacement.append("--replace")
    second = subprocess.run(replacement, capture_output=True, text=True, check=False)
    assert second.returncode == 0, second.stderr + second.stdout
    replaced = json.loads(request_path.read_text(encoding="utf-8"))
    assert replaced["purpose"] == "Coordinate the revised status LED hardware change"
