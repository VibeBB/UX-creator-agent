"""Phase-7 tests: served classification, bold proposals, innovation lens."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ux_creator.contract import Job, UXContract
from ux_creator.gates import run_gates
from ux_creator.projections import write_projections
from ux_creator.proposals import ProposalSet, triage, write_triage
from ux_creator.report import build_report


def _job(importance: int, satisfaction: int) -> Job:
    return Job.model_validate(
        {
            "id": "j",
            "functional": "f",
            "emotional": "e",
            "social": "s",
            "importance": importance,
            "satisfaction": satisfaction,
        }
    )


def test_served_boundaries() -> None:
    # opportunity = importance + max(importance - satisfaction, 0)
    assert _job(10, 10).served == "overserved"  # 10
    assert _job(6, 1).served == "appropriate"  # 11
    assert _job(7, 2).served == "appropriate"  # 12
    assert _job(9, 4).served == "appropriate"  # 14
    assert _job(10, 5).served == "underserved"  # 15
    assert _job(8, 1).served == "underserved"  # 15
    assert _job(10, 1).served == "underserved"  # 19


def _props(*items: dict[str, Any]) -> ProposalSet:
    return ProposalSet.model_validate({"proposals": list(items)})


def _underserved_contract(contract_dict: dict[str, Any]) -> UXContract:
    contract_dict["jobs"][0]["importance"] = 10
    contract_dict["jobs"][0]["satisfaction"] = 1  # opportunity 19
    contract_dict["product"]["surfaces"].append({"id": "web", "layer": "web_ui"})
    return UXContract.model_validate(contract_dict)


def test_bold_needs_theory_break(contract_dict: dict[str, Any]) -> None:
    contract = _underserved_contract(contract_dict)
    triaged = triage(
        contract,
        _props(
            {
                "id": "p",
                "surface": "web",
                "summary": "x",
                "jobs": ["j1"],
                "target_agent": "bard",
                "bold": True,
            }
        ),
    )
    assert triaged[0].status == "needs_theory_break"
    assert triaged[0].bold is True


def test_bold_without_opportunity(contract_dict: dict[str, Any]) -> None:
    # contract_dict job j1: importance 8, satisfaction 5 -> opportunity 11 (appropriate)
    contract = UXContract.model_validate(contract_dict)
    triaged = triage(
        contract,
        _props(
            {
                "id": "p",
                "surface": "btn",
                "summary": "x",
                "jobs": ["j1"],
                "bold": True,
                "theory_break": "HIG: visible controls",
            }
        ),
    )
    assert triaged[0].status == "bold_without_opportunity"
    assert triaged[0].served == {"j1": "appropriate"}


def test_bold_high_risk_and_rationale_prefix(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract = _underserved_contract(contract_dict)
    proposals = _props(
        {
            "id": "p",
            "surface": "web",  # low-risk layer, but bold forces high
            "summary": "kill the button",
            "jobs": ["j1"],
            "rationale": "j1 users hate the extra step",
            "target_agent": "bard",
            "bold": True,
            "theory_break": "HIG: visible controls",
        }
    )
    t = triage(contract, proposals)[0]
    assert t.status == "auto_send"
    assert t.risk == "high"
    assert t.served == {"j1": "underserved"}
    paths = write_triage(contract, proposals, tmp_path)
    request = json.loads(paths["p"].read_text(encoding="utf-8"))
    assert request["risk"] == "high"
    assert request["rationale"].startswith("[bold] breaks: HIG: visible controls — ")


def test_bold_still_needs_rationale(contract_dict: dict[str, Any]) -> None:
    contract = _underserved_contract(contract_dict)
    triaged = triage(
        contract,
        _props(
            {
                "id": "p",
                "surface": "web",
                "summary": "x",
                "jobs": ["j1"],
                "rationale": "no job cited here",
                "target_agent": "bard",
                "bold": True,
                "theory_break": "HIG: visible controls",
            }
        ),
    )
    assert triaged[0].status == "needs_rationale"


def test_innovation_lens(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["jobs"].append(
        {
            "id": "j2",
            "functional": "f",
            "emotional": "e",
            "social": "s",
            "importance": 10,
            "satisfaction": 1,
        }
    )
    contract = UXContract.model_validate(contract_dict)
    report = run_gates(contract, tmp_path)
    proposals = _props(
        {
            "id": "bold_blocked",
            "surface": "btn",
            "summary": "x",
            "jobs": ["j2"],
            "bold": True,  # no theory_break
        }
    )
    write_triage(contract, proposals, tmp_path)
    lens = build_report(contract, report, out_dir=tmp_path)["lenses"]["innovation"]
    assert lens["by_served"]["underserved"] == ["j2"]
    assert lens["by_served"]["appropriate"] == ["j1"]
    assert lens["bold_proposals"] == 1
    assert lens["bold_blocked"] == ["bold_blocked"]
    assert lens["core_experience"] == contract.core_experience


def test_innovation_lens_no_triage(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract = UXContract.model_validate(contract_dict)
    report = run_gates(contract, tmp_path)
    lens = build_report(contract, report, out_dir=tmp_path)["lenses"]["innovation"]
    assert lens["bold_proposals"] == 0
    assert lens["bold_blocked"] == []


def test_odi_csv_served_column(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "x", tmp_path)
    rows = paths["x.odi.csv"].read_text(encoding="utf-8").splitlines()
    assert rows[0].endswith(",served,covered_by")
    assert any(r.startswith("boil,") and ",appropriate," in r for r in rows)
    assert any(r.startswith("keep_warm,") and ",overserved," in r for r in rows)


def test_example_bold_proposal_blocked(example_contract: UXContract) -> None:
    proposals = ProposalSet.model_validate(
        json.loads(
            Path("examples/smart-kettle/smart-kettle.ux-proposals.json").read_text(encoding="utf-8")
        )
    )
    by_id = {t.id: t for t in triage(example_contract, proposals)}
    assert by_id["no_button_boil"].bold is True
    # boil opportunity is 14 (appropriate) — bold lands blocked
    assert by_id["no_button_boil"].status == "bold_without_opportunity"
