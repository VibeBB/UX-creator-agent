"""Sibling import adapters and ux-request writer tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import ValidationError

from ux_creator.contract import UXContract
from ux_creator.imports import extract_touchpoints, import_source
from ux_creator.requests import (
    TARGET_AGENTS,
    UXRequest,
    build_request,
    load_request,
    write_request,
)

NOW = datetime(2025, 1, 1, tzinfo=UTC)


def _build(
    contract: UXContract,
    workspace: Path,
    *,
    request_id: str = "request-one",
    target_agent: str = "mech",
    risk: Literal["low", "high"] = "low",
    purpose: str = "Improve the enclosure interaction",
    rationale: str = "A lower edge makes the button easier to locate.",
    inputs: list[str] | None = None,
    depends_on: list[str] | None = None,
) -> UXRequest:
    return build_request(
        contract,
        id=request_id,
        target_agent=target_agent,
        stage="design",
        risk=risk,
        purpose=purpose,
        rationale=rationale,
        requested_changes=["raise the button"],
        inputs=inputs or [],
        expected_deliverables=["updated enclosure"],
        acceptance=["button can be found by touch"],
        depends_on=depends_on or [],
        workspace=workspace,
        now=NOW,
    )


def test_circuit_extract() -> None:
    data = {
        "system": "circuit",
        "connectors": [
            {"ref": "J1", "housing": "USB-C", "cavities": ["1", "2"]},
            {"ref": "SW1"},
        ],
    }
    assert extract_touchpoints("circuit", data) == ["J1", "SW1", "USB-C"]


def test_mech_extract() -> None:
    data = {
        "system": "mech",
        "anchors": [{"name": "clip_a", "kind": "clip"}, {"name": "grommet_b"}],
    }
    assert extract_touchpoints("mech", data) == ["clip_a", "grommet_b"]


def test_wire_extract() -> None:
    data = {"connectors": [{"id": "C1"}, {"id": "C2"}]}
    assert extract_touchpoints("wire", data) == ["C1", "C2"]


def test_import_records_provenance(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    src = tmp_path / "board.connectivity.json"
    src.write_text(
        json.dumps({"system": "circuit", "connectors": [{"ref": "J1"}]}), encoding="utf-8"
    )
    contract = import_source(UXContract.model_validate(contract_dict), "circuit", src)
    assert contract.imports[0].system == "circuit"
    assert contract.imports[0].extracted == ["J1"]
    assert len(contract.imports[0].sha256) == 64


def test_import_rejects_wrong_system(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    src = tmp_path / "x.envelope.json"
    src.write_text(json.dumps({"system": "mech", "anchors": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="declares system"):
        import_source(UXContract.model_validate(contract_dict), "circuit", src)


def test_request_low_risk(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract = UXContract.model_validate(contract_dict)
    req = _build(contract, tmp_path)
    path = write_request(req, tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 2
    assert data["system"] == "ux-creator"
    assert data["risk"] == "low"
    assert data["created_at"] == NOW.isoformat()
    assert load_request(path) == req


def test_request_high_risk_needs_job_id(contract_dict: dict[str, Any]) -> None:
    contract = UXContract.model_validate(contract_dict)
    with pytest.raises(ValueError, match="job id"):
        _build(
            contract,
            Path("."),
            target_agent="circuit",
            risk="high",
            rationale="just because",
        )


def test_request_high_risk_with_job_id(contract_dict: dict[str, Any]) -> None:
    contract = UXContract.model_validate(contract_dict)
    req = _build(
        contract,
        Path("."),
        target_agent="circuit",
        risk="high",
        rationale="job j1 requires a quieter pump driver",
    )
    assert req.target_agent == "circuit"


def test_request_unknown_target(contract_dict: dict[str, Any]) -> None:
    contract = UXContract.model_validate(contract_dict)
    with pytest.raises(ValueError, match="target_agent"):
    _build(contract, Path("."), target_agent="nobody")


def test_target_agents() -> None:
    assert set(TARGET_AGENTS) == {
        "bard",
        "circuit",
        "dashboard",
        "doc",
        "firmware",
        "fpga",
        "mech",
        "prodeng",
        "sim",
        "wire",
    }


def test_request_hashes_workspace_inputs(
    contract_dict: dict[str, Any], tmp_path: Path
) -> None:
    contract = UXContract.model_validate(contract_dict)
    source = tmp_path / "input.json"
    source.write_text('{"revision":1}\n', encoding="utf-8")
    request = _build(contract, tmp_path, inputs=["input.json"])
    assert request.inputs[0].path == "input.json"
    assert len(request.inputs[0].sha256) == 64
    for value in ("../outside.json", str(source.resolve()), "missing.json"):
        with pytest.raises(ValueError, match="workspace-relative|outside|does not exist"):
            _build(contract, tmp_path, inputs=[value])


def test_request_rejects_short_purpose_and_naive_timestamp(
    contract_dict: dict[str, Any], tmp_path: Path
) -> None:
    contract = UXContract.model_validate(contract_dict)
    request = _build(contract, tmp_path)
    payload = request.model_dump()
    payload["purpose"] = "short"
    with pytest.raises(ValidationError, match="purpose"):
        UXRequest.model_validate(payload)
    payload = request.model_dump()
    payload["created_at"] = "2025-01-01T00:00:00"
    with pytest.raises(ValidationError, match="timezone"):
        UXRequest.model_validate(payload)


@pytest.mark.parametrize(
    "dependencies",
    [["request-one"], ["other", "other"]],
)
def test_request_rejects_self_and_duplicate_dependencies(
    contract_dict: dict[str, Any], tmp_path: Path, dependencies: list[str]
) -> None:
    contract = UXContract.model_validate(contract_dict)
    request = _build(contract, tmp_path)
    payload = request.model_dump()
    payload["depends_on"] = dependencies
    with pytest.raises(ValidationError, match="depends_on"):
        UXRequest.model_validate(payload)


def test_request_writer_refuses_different_overwrite(
    contract_dict: dict[str, Any], tmp_path: Path
) -> None:
    contract = UXContract.model_validate(contract_dict)
    first = _build(contract, tmp_path)
    path = write_request(first, tmp_path)
    assert write_request(first, tmp_path) == path
    second = _build(
        contract, tmp_path, purpose="A different enclosure request"
    )
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_request(second, tmp_path)
    assert write_request(second, tmp_path, replace=True) == path
    assert load_request(path) == second
