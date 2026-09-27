"""Phase-5 tests: advisory reconciliation + review lens."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ux_creator.advisory import (
    VisualFinding,
    load_visual_reviews,
    reconcile_findings,
    write_visual_review,
)
from ux_creator.contract import UXContract
from ux_creator.gates import run_gates
from ux_creator.report import build_report

CONTRACT = "examples/smart-kettle/smart-kettle.ux.json"
LONG_SUMMARY = (
    "The rendered diagram reads cleanly overall, with consistent spacing "
    "and legible labels across every stage and state. Colors, arrows, and "
    "typography match the contract structure closely enough to trust this "
    "review. One minor ambiguity is noted in the findings below!"
)


def _record(tmp_path: Path, findings: list[VisualFinding], name: str = "img") -> Path:
    image = tmp_path / f"{name}.svg"
    image.write_text("<svg/>", encoding="utf-8")
    return write_visual_review(image, "statechart", LONG_SUMMARY, findings)


def _reconcile(contract_dict: dict[str, Any], tmp_path: Path, findings: list[VisualFinding]):
    contract = UXContract.model_validate(contract_dict)
    report = run_gates(contract, tmp_path)
    _record(tmp_path, findings)
    records, malformed = load_visual_reviews(tmp_path)
    assert malformed == []
    return reconcile_findings(contract, report, records)


def _orphan_contract(contract_dict: dict[str, Any]) -> dict[str, Any]:
    contract_dict["statecharts"][0]["states"].append({"id": "z", "final": True})
    return contract_dict


def test_unreachable_corroborated(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    findings = _reconcile(
        _orphan_contract(contract_dict),
        tmp_path,
        [VisualFinding(category="unreachable_state", where="z", observation="o")],
    )
    assert findings[0].reconciliation == "corroborated"
    assert "unreachable" in findings[0].reason


def test_unreachable_contradicted(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    findings = _reconcile(
        contract_dict,
        tmp_path,
        [VisualFinding(category="unreachable_state", where="a", observation="o")],
    )
    assert findings[0].reconciliation == "contradicted"
    assert "reachable" in findings[0].reason


def test_unreachable_unverifiable(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    findings = _reconcile(
        contract_dict,
        tmp_path,
        [VisualFinding(category="unreachable_state", where="ghost", observation="o")],
    )
    assert findings[0].reconciliation == "unverifiable"


def test_missing_touchpoint_corroborated(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["imports"] = [
        {
            "system": "circuit",
            "path": "c.connectivity.json",
            "sha256": "sha256:" + "0" * 64,
            "extracted": ["j2"],
        }
    ]
    findings = _reconcile(
        contract_dict,
        tmp_path,
        [VisualFinding(category="missing_touchpoint", where="j2", observation="o")],
    )
    assert findings[0].reconciliation == "corroborated"


def test_missing_touchpoint_contradicted(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    findings = _reconcile(
        contract_dict,
        tmp_path,
        [VisualFinding(category="missing_touchpoint", where="btn", observation="o")],
    )
    assert findings[0].reconciliation == "contradicted"


def test_missing_touchpoint_unverifiable(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    findings = _reconcile(
        contract_dict,
        tmp_path,
        [VisualFinding(category="missing_touchpoint", where="nope", observation="o")],
    )
    assert findings[0].reconciliation == "unverifiable"


def test_broken_flow_contradicted(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    findings = _reconcile(
        contract_dict,
        tmp_path,
        [VisualFinding(category="broken_flow", where="a -> b", observation="o")],
    )
    assert findings[0].reconciliation == "contradicted"


def test_broken_flow_corroborated(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    findings = _reconcile(
        contract_dict,
        tmp_path,
        [VisualFinding(category="broken_flow", where="b->a", observation="o")],
    )
    assert findings[0].reconciliation == "corroborated"


def test_broken_flow_unverifiable(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    findings = _reconcile(
        contract_dict,
        tmp_path,
        [VisualFinding(category="broken_flow", where="x->y", observation="o")],
    )
    assert findings[0].reconciliation == "unverifiable"


def test_visual_only_category(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    findings = _reconcile(
        contract_dict,
        tmp_path,
        [VisualFinding(category="label_collision", severity="major", where="a", observation="o")],
    )
    assert findings[0].reconciliation == "unverifiable"
    assert findings[0].reason == "visual-only category"


def test_malformed_record_listed_not_raised(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    bad = tmp_path / "review-visual-broken.advisory.json"
    bad.write_text("{not json", encoding="utf-8")
    _record(tmp_path, [], "fine")
    records, malformed = load_visual_reviews(tmp_path)
    assert len(records) == 1
    assert malformed == [bad]


def test_review_lens_and_images_without_record(
    contract_dict: dict[str, Any], tmp_path: Path
) -> None:
    contract = UXContract.model_validate(contract_dict)
    report = run_gates(contract, tmp_path)
    _record(
        tmp_path,
        [VisualFinding(category="unreachable_state", where="a", observation="o")],
        name="reviewed",
    )
    (tmp_path / "unreviewed.png").write_bytes(b"png")
    lens = build_report(contract, report, out_dir=tmp_path)["lenses"]["review"]
    assert lens["records"] == 1
    assert lens["reconciliation"] == {
        "corroborated": 0,
        "contradicted": 1,
        "unverifiable": 0,
    }
    assert lens["contradicted"] == [
        {
            "category": "unreachable_state",
            "where": "a",
            "record": str(tmp_path / "review-visual-reviewed.advisory.json"),
        }
    ]
    assert lens["images_without_record"] == [str(tmp_path / "unreviewed.png")]


def test_verdict_independent_of_advisory(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract = UXContract.model_validate(contract_dict)
    report = run_gates(contract, tmp_path)
    base = build_report(contract, report, out_dir=tmp_path)
    _record(
        tmp_path,
        [
            VisualFinding(
                category="unreachable_state",
                severity="major",
                where="a",
                observation="o",
            )
        ],
    )
    with_advisory = build_report(contract, report, out_dir=tmp_path)
    assert base["verdict"] == with_advisory["verdict"]
    assert with_advisory["lenses"]["review"]["reconciliation"]["contradicted"] == 1


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ux_creator", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_review_reconcile_round_trip(tmp_path: Path) -> None:
    _record(
        tmp_path,
        [VisualFinding(category="unreachable_state", where="idle", observation="o")],
        name="chart",
    )
    proc = _run(
        "review-reconcile",
        "--contract",
        CONTRACT,
        "--out-dir",
        str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["verdict"] == "pass"
    assert payload["stage"] == "review-reconcile"
    assert len(payload["findings"]) == 1
    assert payload["findings"][0]["reconciliation"] == "contradicted"
    assert payload["malformed"] == []
