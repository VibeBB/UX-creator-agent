"""Phase-8 tests: stage→job linkage and the opportunity coverage gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ux_creator.contract import UXContract
from ux_creator.gates import run_gates
from ux_creator.projections import write_projections
from ux_creator.report import build_report

CONTRACT = "examples/smart-kettle/smart-kettle.ux.json"


def _contract(payload: dict[str, Any]) -> UXContract:
    return UXContract.model_validate(payload)


def _check(report: Any, check_id: str) -> Any:
    return next(c for c in report.checks if c.id == check_id)


def test_stage_jobs_unknown_rejected(contract_dict: dict[str, Any]) -> None:
    contract_dict["journeys"][0]["stages"][0]["jobs"] = ["ghost"]
    with pytest.raises(ValueError, match="unknown job ids"):
        _contract(contract_dict)


def test_stage_links_unknown_when_unlinked(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    # jobs declared but no stage links any of them -> warn, not fail
    contract_dict["journeys"][0]["stages"][0]["jobs"] = []
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "opportunity.stage_links").status == "unknown"
    assert "coverage cannot be judged" in _check(report, "opportunity.stage_links").detail


def test_coverage_pass_no_underserved(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["journeys"][0]["stages"][0]["jobs"] = ["j1"]
    report = run_gates(_contract(contract_dict), tmp_path)
    check = _check(report, "opportunity.coverage")
    assert check.status == "pass"
    assert check.detail == "no underserved jobs"


def test_coverage_fail_uncovered_underserved(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    # j1 -> opportunity 19 (underserved), no stage links it
    contract_dict["jobs"][0]["importance"] = 10
    contract_dict["jobs"][0]["satisfaction"] = 1
    contract_dict["journeys"][0]["stages"][0]["jobs"] = []
    report = run_gates(_contract(contract_dict), tmp_path)
    check = _check(report, "opportunity.coverage")
    assert check.status == "fail"
    assert "uncovered underserved: j1" in check.detail
    assert report.verdict == "fail"


def test_coverage_pass_underserved_linked(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["jobs"][0]["importance"] = 10
    contract_dict["jobs"][0]["satisfaction"] = 1
    contract_dict["journeys"][0]["stages"][0]["jobs"] = ["j1"]
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "opportunity.coverage").status == "pass"
    assert _check(report, "opportunity.stage_links").status == "pass"


def test_odi_covered_by_column(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "x", tmp_path)
    rows = paths["x.odi.csv"].read_text(encoding="utf-8").splitlines()
    assert rows[0].endswith(",covered_by")
    boil = next(r for r in rows if r.startswith("boil,"))
    assert "morning.fill" in boil and "morning.boil" in boil
    keep_warm = next(r for r in rows if r.startswith("keep_warm,"))
    assert keep_warm.endswith("morning.forgot")


def test_journey_mmd_jobs_label(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "x", tmp_path)
    mmd = next(p for k, p in paths.items() if k.endswith(".journey.mmd"))
    text = mmd.read_text(encoding="utf-8")
    assert "section boil [jobs: boil]" in text


def test_innovation_lens_coverage(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["jobs"][0]["importance"] = 10
    contract_dict["jobs"][0]["satisfaction"] = 1
    contract_dict["journeys"][0]["stages"][0]["jobs"] = []
    contract = _contract(contract_dict)
    report = run_gates(contract, tmp_path)
    lens = build_report(contract, report, out_dir=tmp_path)["lenses"]["innovation"]
    assert lens["uncovered_underserved"] == ["j1"]
    contract_dict["journeys"][0]["stages"][0]["jobs"] = ["j1"]
    contract = _contract(contract_dict)
    lens = build_report(contract, report, out_dir=tmp_path)["lenses"]["innovation"]
    assert lens["coverage"] == {"j1": ["jn.s1"]}
    assert lens["uncovered_underserved"] == []


def test_example_contract_stage_jobs() -> None:
    contract = UXContract.model_validate(json.loads(Path(CONTRACT).read_text(encoding="utf-8")))
    stages = {s.id: s for j in contract.journeys for s in j.stages}
    assert stages["pair_app"].jobs == []
    assert stages["fill"].jobs == ["boil"]
    assert stages["boil"].jobs == ["boil"]
    assert stages["pour"].jobs == ["boil"]
    assert stages["forgot"].jobs == ["keep_warm"]
