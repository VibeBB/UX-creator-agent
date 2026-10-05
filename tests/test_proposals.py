"""Phase-4 tests: QCD triage of change proposals."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from ux_creator.contract import UXContract
from ux_creator.proposals import (
    ChangeProposal,
    ProposalSet,
    TriagedProposal,
    triage,
    write_triage,
)

CONTRACT = "examples/smart-kettle/smart-kettle.ux.json"
PROPOSALS = "examples/smart-kettle/smart-kettle.ux-proposals.json"


def _props(*items: dict[str, Any]) -> ProposalSet:
    return ProposalSet.model_validate({"proposals": list(items)})


def _by_id(triaged: list[TriagedProposal]) -> dict[str, TriagedProposal]:
    return {t.id: t for t in triaged}


def test_unknown_surface(contract_dict: dict[str, Any]) -> None:
    contract = UXContract.model_validate(contract_dict)
    triaged = triage(contract, _props({"id": "p", "surface": "ghost", "summary": "x"}))
    t = triaged[0]
    assert t.status == "unknown_surface"
    assert t.layer is None
    assert t.risk == "high"


def test_unknown_job(contract_dict: dict[str, Any]) -> None:
    contract = UXContract.model_validate(contract_dict)
    triaged = triage(
        contract,
        _props({"id": "p", "surface": "btn", "summary": "x", "jobs": ["nope"]}),
    )
    assert triaged[0].status == "unknown_job"


def test_dashboard_handles_app_layers(example_contract: UXContract) -> None:
    triaged = triage(
        example_contract,
        _props(
            {
                "id": "p",
                "surface": "mobile_app",
                "summary": "x",
                "jobs": ["boil"],
            }
        ),
    )
    t = triaged[0]
    assert t.status == "auto_send"
    assert t.layer == "smartphone_app"
    assert t.risk == "low"
    assert t.target_agent == "dashboard"


def test_needs_rationale_high_risk(example_contract: UXContract) -> None:
    triaged = triage(
        example_contract,
        _props({"id": "p", "surface": "hardware_button", "summary": "x", "jobs": ["boil"]}),
    )
    t = triaged[0]
    assert t.status == "needs_rationale"
    assert t.risk == "high"
    assert t.target_agent == "mech"


def test_auto_send_high_risk_with_cited_job(example_contract: UXContract) -> None:
    triaged = triage(
        example_contract,
        _props(
            {
                "id": "p",
                "surface": "status_led",
                "summary": "x",
                "jobs": ["keep_warm"],
                "rationale": "keep_warm needs ambient feedback",
            }
        ),
    )
    t = triaged[0]
    assert t.status == "auto_send"
    assert t.risk == "high"
    assert t.target_agent == "circuit"


def test_auto_send_low_risk_via_target_override(contract_dict: dict[str, Any]) -> None:
    contract_dict["product"]["surfaces"].append({"id": "web", "layer": "web_ui"})
    contract = UXContract.model_validate(contract_dict)
    triaged = triage(
        contract,
        _props(
            {
                "id": "p",
                "surface": "web",
                "summary": "x",
                "jobs": ["j1"],
                "target_agent": "bard",
            }
        ),
    )
    t = triaged[0]
    assert t.status == "auto_send"
    assert t.risk == "low"
    assert t.target_agent == "bard"


def test_cost_and_delivery_escalate_risk(contract_dict: dict[str, Any]) -> None:
    contract_dict["product"]["surfaces"].append({"id": "web", "layer": "web_ui"})
    contract = UXContract.model_validate(contract_dict)
    for extra in ({"cost": "high"}, {"delivery": "slow"}):
        triaged = triage(
            contract,
            _props(
                {
                    "id": "p",
                    "surface": "web",
                    "summary": "x",
                    "jobs": ["j1"],
                    "target_agent": "bard",
                    **extra,
                }
            ),
        )
        assert triaged[0].risk == "high"
        assert triaged[0].status == "needs_rationale"


def test_sorted_by_opportunity(example_contract: UXContract) -> None:
    triaged = triage(
        example_contract,
        _props(
            {
                "id": "low_opp",
                "surface": "status_led",
                "summary": "x",
                "jobs": ["keep_warm"],
                "rationale": "keep_warm",
            },
            {
                "id": "high_opp",
                "surface": "buzzer",
                "summary": "x",
                "jobs": ["boil"],
                "rationale": "boil",
            },
        ),
    )
    assert [t.id for t in triaged] == ["high_opp", "low_opp"]
    assert triaged[0].opportunity > triaged[1].opportunity


def test_invalid_target_agent_raises(contract_dict: dict[str, Any]) -> None:
    contract = UXContract.model_validate(contract_dict)
    proposals = _props({"id": "p", "surface": "btn", "summary": "x", "target_agent": "ghost"})
    with pytest.raises(ValueError, match="unknown target_agent"):
        triage(contract, proposals)


def test_proposal_model_rejects_extra() -> None:
    with pytest.raises(Exception, match="extra"):
        ChangeProposal.model_validate({"id": "p", "surface": "s", "summary": "x", "bogus": 1})


def test_write_triage_writes_requests_only_for_auto_send(
    example_contract: UXContract, tmp_path: Path
) -> None:
    proposals = _props(
        {
            "id": "sent",
            "surface": "status_led",
            "summary": "dim the led",
            "jobs": ["keep_warm"],
            "rationale": "keep_warm",
        },
        {"id": "held", "surface": "hardware_button", "summary": "swap", "jobs": ["boil"]},
        {"id": "unserved", "surface": "mobile_app", "summary": "tour"},
    )
    paths = write_triage(example_contract, proposals, tmp_path)
    assert "triage" in paths and "sent" in paths
    assert "held" not in paths and "unserved" not in paths
    triage_doc = json.loads(paths["triage"].read_text(encoding="utf-8"))
    assert triage_doc["schema_version"] == 1
    assert triage_doc["contract_sha256"].startswith("sha256:")
    assert len(triage_doc["triaged"]) == 3
    triaged = {item["id"]: item for item in triage_doc["triaged"]}
    assert triaged["unserved"]["status"] == "no_job"
    request = json.loads(paths["sent"].read_text(encoding="utf-8"))
    assert request["system"] == "ux-creator"
    assert request["target_agent"] == "circuit"
    assert request["risk"] == "high"
    assert request["requested_changes"] == ["dim the led"]


def test_example_proposals_file_statuses(example_contract: UXContract) -> None:
    proposals = ProposalSet.model_validate(json.loads(Path(PROPOSALS).read_text(encoding="utf-8")))
    statuses = _by_id(triage(example_contract, proposals))
    assert statuses["app_onboard_tour"].status == "auto_send"
    assert statuses["app_onboard_tour"].target_agent == "dashboard"
    assert statuses["led_brightness"].status == "auto_send"
    assert statuses["led_brightness"].target_agent == "circuit"
    assert statuses["capacitive_button"].status == "needs_rationale"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ux_creator", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_propose_round_trip(tmp_path: Path) -> None:
    proc = _run(
        "propose",
        "--contract",
        CONTRACT,
        "--proposals",
        PROPOSALS,
        "--out-dir",
        str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["verdict"] == "pass"
    assert payload["stage"] == "propose"
    assert payload["blocked"] == ["capacitive_button", "no_button_boil"]
    written = {Path(p).name for p in payload["written"].values()}
    assert "smart-kettle.triage.json" in written
    assert "smart-kettle-led-brightness.ux-request.json" in written


def test_cli_propose_fail_closed(tmp_path: Path) -> None:
    bad = tmp_path / "bad.ux-proposals.json"
    bad.write_text('{"schema_version":1,"system":"ux-creator","proposals":[]}', encoding="utf-8")
    proc = _run(
        "propose",
        "--contract",
        CONTRACT,
        "--proposals",
        str(bad),
        "--out-dir",
        str(tmp_path / "out"),
    )
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["verdict"] == "fail"
