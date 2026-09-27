"""Gate tests, including negative cases that corrupt the judged input."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from ux_creator.contract import UXContract
from ux_creator.gates import run_gates


def _contract(payload: dict[str, Any]) -> UXContract:
    return UXContract.model_validate(payload)


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
