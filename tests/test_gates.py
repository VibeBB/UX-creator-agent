"""Gate tests, including negative cases that corrupt the judged input."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from ux_creator.contract import UXContract
from ux_creator.gates import UNKNOWN, GateCheck, run_gates


def _contract(payload: dict[str, Any]) -> UXContract:
    return UXContract.model_validate(payload)


def test_check_error_is_unknown_with_exception_type(
    example_contract: UXContract, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_contract: UXContract) -> list[GateCheck]:
        raise KeyError("missing")

    monkeypatch.setattr("ux_creator.gates._statechart_checks", fail)
    report = run_gates(example_contract, tmp_path)
    checks = [check for check in report.checks if check.id == "statechart"]

    assert len(checks) == 1
    assert checks[0].status == UNKNOWN
    assert "KeyError" in checks[0].detail


def test_example_passes(example_contract: UXContract, tmp_path: Path) -> None:
    report = run_gates(example_contract, tmp_path)
    assert report.verdict == "pass", [c for c in report.checks if c.status != "pass"]


def test_minimal_passes(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    assert run_gates(_contract(contract_dict), tmp_path).verdict == "pass"


def test_no_statecharts_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    del contract_dict["statecharts"]
    report = run_gates(_contract(contract_dict), tmp_path)
    assert report.verdict == "fail"
    assert any(c.id == "statechart.present" and c.status == "fail" for c in report.checks)


def test_two_initial_states_fail(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["statecharts"][0]["states"][1]["initial"] = True
    contract_dict["statecharts"][0]["states"][1]["final"] = False
    report = run_gates(_contract(contract_dict), tmp_path)
    assert any(c.id.endswith("single_initial") and c.status == "fail" for c in report.checks)


def test_unreachable_state_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["statecharts"][0]["states"].append({"id": "orphan"})
    report = run_gates(_contract(contract_dict), tmp_path)
    assert any(c.id.endswith("reachability") and c.status == "fail" for c in report.checks)


def test_dead_end_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["statecharts"][0]["states"][1]["final"] = False
    report = run_gates(_contract(contract_dict), tmp_path)
    assert any(c.id.endswith("no_dead_end") and c.status == "fail" for c in report.checks)


def test_undeclared_surface_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["journeys"][0]["stages"][0]["surfaces"].append("ghost")
    report = run_gates(_contract(contract_dict), tmp_path)
    assert any(c.id.endswith("surfaces_declared") and c.status == "fail" for c in report.checks)


def test_low_emotion_without_pain_point_fails(
    contract_dict: dict[str, Any], tmp_path: Path
) -> None:
    contract_dict["journeys"][0]["stages"][0]["emotion"] = 1
    report = run_gates(_contract(contract_dict), tmp_path)
    assert any(c.id.endswith("pain_points_recorded") and c.status == "fail" for c in report.checks)


def test_thin_job_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["jobs"][0]["emotional"] = ""
    report = run_gates(_contract(contract_dict), tmp_path)
    assert any(c.id == "jobs.three_dimensions" and c.status == "fail" for c in report.checks)


def test_import_sha_mismatch_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    src = tmp_path / "board.connectivity.json"
    src.write_text(json.dumps({"system": "circuit", "connectors": []}), encoding="utf-8")
    contract_dict["imports"] = [
        {"system": "circuit", "path": "board.connectivity.json", "sha256": "0" * 64}
    ]
    report = run_gates(_contract(contract_dict), tmp_path)
    assert any(c.id.startswith("imports.") and c.status == "fail" for c in report.checks)


def test_import_missing_file_unknown(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["imports"] = [{"system": "circuit", "path": "gone.json", "sha256": "0" * 64}]
    report = run_gates(_contract(contract_dict), tmp_path)
    assert any(c.id.startswith("imports.") and c.status == "unknown" for c in report.checks)
    assert report.verdict == "fail"


def test_import_sha_match_passes(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    import hashlib

    src = tmp_path / "board.connectivity.json"
    body = json.dumps({"system": "circuit", "connectors": []})
    src.write_text(body, encoding="utf-8")
    contract_dict["imports"] = [
        {
            "system": "circuit",
            "path": "board.connectivity.json",
            "sha256": hashlib.sha256(body.encode()).hexdigest(),
        }
    ]
    assert run_gates(_contract(contract_dict), tmp_path).verdict == "pass"


def test_corrupt_check_unknown_is_fail_closed(
    contract_dict: dict[str, Any], tmp_path: Path
) -> None:
    """A gate that cannot run reports unknown, which fails the verdict."""
    contract = _contract(copy.deepcopy(contract_dict))
    contract_dict["imports"] = [{"system": "mech", "path": "missing.envelope.json", "sha256": "x"}]
    report = run_gates(_contract(contract_dict), tmp_path)
    assert report.verdict == "fail"
    assert contract


def _oobe(contract_dict: dict[str, Any], max_steps: int) -> dict[str, str]:
    payload = copy.deepcopy(contract_dict)
    payload["oobe"] = {
        "statechart": "sc",
        "ready_state": "b",
        "max_steps": max_steps,
        "rationale": "first brew within one press",
    }
    payload["journeys"][0]["stages"][0]["kind"] = "onboard"
    report = run_gates(_contract(payload))
    return {c.id: c.status for c in report.checks if c.id.startswith("oobe.")}


def test_oobe_step_budget_boundary(contract_dict: dict[str, Any]) -> None:
    payload = copy.deepcopy(contract_dict)
    chart = payload["statecharts"][0]
    chart["states"].insert(1, {"id": "pair"})
    chart["transitions"] = [
        {"from": "a", "event": "unbox", "to": "pair"},
        {"from": "pair", "event": "paired", "to": "b"},
    ]
    assert _oobe(payload, 1)["oobe.steps"] == "fail"
    assert _oobe(payload, 2)["oobe.steps"] == "pass"
    assert _oobe(payload, 3)["oobe.steps"] == "pass"
    assert _oobe(payload, 2)["oobe.journey"] == "pass"


def test_oobe_without_onboard_stage_fails(contract_dict: dict[str, Any]) -> None:
    payload = copy.deepcopy(contract_dict)
    payload["oobe"] = {
        "statechart": "sc",
        "ready_state": "b",
        "max_steps": 5,
        "rationale": "first brew within one press",
    }
    statuses = {c.id: c.status for c in run_gates(_contract(payload)).checks}
    assert statuses["oobe.journey"] == "fail"


def test_oobe_unreachable_ready_state_fails(contract_dict: dict[str, Any]) -> None:
    payload = copy.deepcopy(contract_dict)
    payload["statecharts"][0]["transitions"] = []
    assert _oobe(payload, 5)["oobe.steps"] == "fail"


@pytest.mark.parametrize(
    ("field", "value"),
    [("statechart", "nope"), ("ready_state", "nope"), ("max_steps", 0), ("max_steps", 51)],
)
def test_oobe_rejects_unknown_refs_and_bounds(
    contract_dict: dict[str, Any], field: str, value: object
) -> None:
    payload = copy.deepcopy(contract_dict)
    oobe: dict[str, object] = {
        "statechart": "sc",
        "ready_state": "b",
        "max_steps": 5,
        "rationale": "first brew within one press",
    }
    oobe[field] = value
    payload["oobe"] = oobe
    with pytest.raises(ValueError):
        _contract(payload)


def _in_box(contract_dict: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    payload = copy.deepcopy(contract_dict)
    chart = payload["statecharts"][0]
    chart["states"].insert(1, {"id": "pair"})
    chart["transitions"] = [
        {"from": "a", "event": "unbox", "to": "pair"},
        {"from": "pair", "event": "paired", "to": "b"},
    ]
    payload["oobe"] = {
        "statechart": "sc",
        "ready_state": "b",
        "max_steps": 5,
        "rationale": "first brew within one press",
        "in_box": items,
    }
    return payload


def _in_box_status(payload: dict[str, Any]) -> GateCheck:
    return next(c for c in run_gates(_contract(payload)).checks if c.id == "oobe.in_box")


@pytest.mark.parametrize(
    ("guide_state", "status"), [("a", "pass"), ("pair", "pass"), ("b", "fail")]
)
def test_in_box_first_use_order_boundary(
    contract_dict: dict[str, Any], guide_state: str, status: str
) -> None:
    items = [
        {"id": "guide", "name": "Quick start", "kind": "document", "first_used_state": guide_state},
        {"id": "kettle", "name": "Kettle", "kind": "product", "first_used_state": "pair"},
        {"id": "cord", "name": "Power cord", "kind": "cable"},
    ]
    check = _in_box_status(_in_box(contract_dict, items))
    assert check.status == status
    if status == "fail":
        assert check.detail == "kettle (step 1) listed under guide"


def test_in_box_unreachable_state_fails_and_empty_list_emits_nothing(
    contract_dict: dict[str, Any],
) -> None:
    items = [{"id": "kettle", "name": "Kettle", "kind": "product", "first_used_state": "b"}]
    payload = _in_box(contract_dict, items)
    payload["statecharts"][0]["transitions"] = [{"from": "b", "event": "x", "to": "a"}]
    assert _in_box_status(payload).status == "fail"
    report = run_gates(_contract(_in_box(contract_dict, [])))
    assert "oobe.in_box" not in {c.id for c in report.checks}


@pytest.mark.parametrize(
    "items",
    [
        [{"id": "a1", "name": "A", "kind": "accessory"}],
        [
            {"id": "k", "name": "K", "kind": "product"},
            {"id": "k", "name": "K2", "kind": "cable"},
        ],
        [{"id": "k", "name": "K", "kind": "product", "first_used_state": "nope"}],
    ],
    ids=["no-product", "duplicate", "unknown-state"],
)
def test_in_box_rejects_malformed_lists(
    contract_dict: dict[str, Any], items: list[dict[str, Any]]
) -> None:
    with pytest.raises(ValueError):
        _contract(_in_box(contract_dict, items))


def test_import_sidecar_checked_when_present(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    import hashlib

    from ux_creator._envelope import sidecar_path, write_envelope

    src = tmp_path / "board.connectivity.json"
    src.write_text(json.dumps({"system": "circuit", "connectors": []}), encoding="utf-8")
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    contract_dict["imports"] = [
        {"system": "circuit", "path": "board.connectivity.json", "sha256": digest}
    ]
    cid = "imports.circuit:board.connectivity.json.provenance"

    def status() -> str | None:
        report = run_gates(_contract(contract_dict), tmp_path)
        return next((c.status for c in report.checks if c.id == cid), None)

    assert status() is None  # authored contracts carry no sidecar
    write_envelope(src, "circuit", [], tmp_path)
    assert status() == "pass"
    sidecar = sidecar_path(src)
    body = json.loads(sidecar.read_text(encoding="utf-8"))
    sidecar.write_text(json.dumps(body | {"producer": "mech"}), encoding="utf-8")
    assert status() == "fail"
    body["artifact"]["sha256"] = "0" * 64
    sidecar.write_text(json.dumps(body), encoding="utf-8")
    assert status() == "fail"
