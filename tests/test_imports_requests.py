"""Sibling import adapters and ux-request writer tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ux_creator.contract import UXContract
from ux_creator.imports import extract_touchpoints, import_source
from ux_creator.requests import TARGET_AGENTS, build_request, write_request


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
    req = build_request(
        contract,
        target_agent="mech",
        risk="low",
        rationale="color change",
        requested_changes=["lighter lid"],
    )
    path = write_request(req, tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["system"] == "ux-creator"
    assert data["risk"] == "low"


def test_request_high_risk_needs_job_id(contract_dict: dict[str, Any]) -> None:
    contract = UXContract.model_validate(contract_dict)
    with pytest.raises(ValueError, match="job id"):
        build_request(
            contract,
            target_agent="circuit",
            risk="high",
            rationale="just because",
            requested_changes=["new board"],
        )


def test_request_high_risk_with_job_id(contract_dict: dict[str, Any]) -> None:
    contract = UXContract.model_validate(contract_dict)
    req = build_request(
        contract,
        target_agent="circuit",
        risk="high",
        rationale="job j1 requires a quieter pump driver",
        requested_changes=["swap MOSFET"],
    )
    assert req.target_agent == "circuit"


def test_request_unknown_target(contract_dict: dict[str, Any]) -> None:
    contract = UXContract.model_validate(contract_dict)
    with pytest.raises(ValueError, match="target_agent"):
        build_request(
            contract,
            target_agent="nobody",
            risk="low",
            rationale="",
            requested_changes=["x"],
        )


def test_target_agents() -> None:
    assert set(TARGET_AGENTS) == {"wire", "mech", "circuit", "bard"}
