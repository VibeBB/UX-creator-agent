from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from ux_creator import cli
from ux_creator.production import (
    ProductionPlan,
    load_plan,
    production_status,
    run_production_gates,
    write_production,
)
from ux_creator.render import RenderResult

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT = REPO_ROOT / "examples" / "smart-kettle-product"
PLAN = PRODUCT / "smart-kettle.production.json"


@pytest.fixture()
def plan_dict() -> dict[str, Any]:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def _ws(plan: dict[str, Any], wid: str) -> dict[str, Any]:
    return next(w for w in plan["workstreams"] if w["id"] == wid)


def _statuses(plan: dict[str, Any], workspace: Path = PRODUCT) -> dict[str, str]:
    report = run_production_gates(
        ProductionPlan.model_validate(plan), workspace, workspace / "requests"
    )
    return {c.id: c.status for c in report.checks}


def test_example_plan_passes() -> None:
    plan = load_plan(PLAN)
    report = run_production_gates(plan, PRODUCT, PRODUCT / "requests")
    assert report.verdict == "pass", [c for c in report.checks if c.status != "pass"]
    assert {c.id for c in report.checks} == {
        "production.acyclic",
        "production.stage_order",
        "production.dependency_status",
        "production.blockers_explained",
        "production.done_has_artifacts",
        "production.requests_answered",
        "production.request_owner",
        "production.liaison_integrity",
        "production.sister_records",
        "production.evidence_loop",
        "production.ux_contract",
    }


def test_status_projection(tmp_path: Path) -> None:
    plan = load_plan(PLAN)
    report = run_production_gates(plan, PRODUCT, PRODUCT / "requests")
    status = production_status(plan, report, PRODUCT, PRODUCT / "requests")
    assert status["current_stage"] == "design"
    assert [a["id"] for a in status["next_actions"]] == ["user_manual"]  # type: ignore[index]
    assert status["blocked"] == [{"id": "pcb_order", "holds": ["decision pcb_vendor"]}]
    paths = write_production(
        plan, report, "smart-kettle", tmp_path, PLAN, PRODUCT, PRODUCT / "requests"
    )
    assert set(paths) == {
        "smart-kettle.production.mmd",
        "smart-kettle.production-status.json",
        "smart-kettle.production-status.md",
    }
    again = write_production(
        plan, report, "smart-kettle", tmp_path / "again", PLAN, PRODUCT, PRODUCT / "requests"
    )
    for name, path in paths.items():
        assert again[name].read_bytes() == path.read_bytes()
    mmd = paths["smart-kettle.production.mmd"].read_text(encoding="utf-8")
    assert mmd.startswith("flowchart LR\n")
    assert "circuit_rev_a --> pcb_order" in mmd


def _mutate(plan: dict[str, Any], case: str) -> None:
    cues = _ws(plan, "sound_cues")
    decision: dict[str, Any] = plan["decisions"][0]
    if case == "unknown_dep":
        cues["depends_on"].append("nope")
    elif case == "self_dep":
        cues["depends_on"].append("sound_cues")
    elif case == "duplicate":
        plan["workstreams"].append(dict(cues))
    elif case == "decision_blocks_unknown":
        decision["blocks"].append("nope")
    elif case == "decided_empty":
        decision["status"] = "decided"
    elif case == "open_with_decision":
        decision["decision"] = "local"
    elif case == "bad_owner":
        cues["owner"] = "marketing"
    elif case == "bad_stage":
        cues["stage"] = "launch"
    else:
        plan["extra"] = True


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("unknown_dep", "unknown dependencies"),
        ("self_dep", "itself"),
        ("duplicate", "duplicate"),
        ("decision_blocks_unknown", "blocks unknown"),
        ("decided_empty", "without a decision"),
        ("open_with_decision", "open but has"),
        ("bad_owner", "owner"),
        ("bad_stage", "stage"),
        ("extra", "extra"),
    ],
)
def test_plan_validation(plan_dict: dict[str, Any], case: str, message: str) -> None:
    _mutate(plan_dict, case)
    with pytest.raises(ValueError, match=message):
        ProductionPlan.model_validate(plan_dict)


def test_cycle_fails(plan_dict: dict[str, Any]) -> None:
    _ws(plan_dict, "ux_contract")["depends_on"] = ["sound_cues"]
    assert _statuses(plan_dict)["production.acyclic"] == "fail"


def test_dependency_on_later_stage_fails(plan_dict: dict[str, Any]) -> None:
    _ws(plan_dict, "circuit_rev_a")["depends_on"].append("boil_bench")
    assert _statuses(plan_dict)["production.stage_order"] == "fail"


def test_started_before_dependencies_fails(plan_dict: dict[str, Any]) -> None:
    _ws(plan_dict, "firmware_feedback")["status"] = "in_progress"
    assert _statuses(plan_dict)["production.dependency_status"] == "fail"


def test_blocked_without_hold_fails(plan_dict: dict[str, Any]) -> None:
    plan_dict["decisions"] = []
    assert _statuses(plan_dict)["production.blockers_explained"] == "fail"


def test_open_blocker_explains_block(plan_dict: dict[str, Any]) -> None:
    plan_dict["decisions"] = []
    plan_dict["blockers"] = [
        {"id": "gerber_drc", "workstream": "pcb_order", "description": "DRC fails on vias"}
    ]
    assert _statuses(plan_dict)["production.blockers_explained"] == "pass"


def test_done_with_open_blocker_fails(plan_dict: dict[str, Any]) -> None:
    _ws(plan_dict, "sound_cues")["status"] = "done"
    plan_dict["blockers"] = [
        {"id": "late", "workstream": "sound_cues", "description": "piezo too quiet"}
    ]
    assert _statuses(plan_dict)["production.blockers_explained"] == "fail"


def test_done_without_artifacts_fails(plan_dict: dict[str, Any]) -> None:
    _ws(plan_dict, "sound_cues")["status"] = "done"
    _ws(plan_dict, "sound_cues")["artifacts"] = []
    assert _statuses(plan_dict)["production.done_has_artifacts"] == "fail"


def test_done_with_missing_artifact_fails(plan_dict: dict[str, Any]) -> None:
    _ws(plan_dict, "sound_cues")["status"] = "done"
    _ws(plan_dict, "sound_cues")["artifacts"] = ["cues/none.json"]
    assert _statuses(plan_dict)["production.done_has_artifacts"] == "fail"


def test_done_without_accepted_response_fails(plan_dict: dict[str, Any]) -> None:
    mech = _ws(plan_dict, "mech_enclosure")
    mech["status"] = "done"
    mech["artifacts"] = ["smart-kettle.ux.json"]
    assert _statuses(plan_dict)["production.requests_answered"] == "fail"


def test_missing_request_is_unknown(plan_dict: dict[str, Any]) -> None:
    _ws(plan_dict, "circuit_rev_a")["request"] = "smart-kettle-nope"
    assert _statuses(plan_dict)["production.requests_answered"] == "unknown"


def test_no_liaison_dir_is_unknown(plan_dict: dict[str, Any]) -> None:
    report = run_production_gates(ProductionPlan.model_validate(plan_dict), PRODUCT, None)
    statuses = {c.id: c.status for c in report.checks}
    assert statuses["production.requests_answered"] == "unknown"
    assert report.verdict == "fail"


def _evaluated(plan: dict[str, Any], workspace: Path) -> dict[str, Any]:
    for w in plan["workstreams"]:
        if w["id"] == "sound_cues":
            w["status"] = "done"
            w["request"] = ""
        if w["id"] in {"circuit_rev_a", "mech_enclosure", "firmware_feedback", "pcb_order"}:
            w["status"] = "done"
            w["artifacts"] = ["smart-kettle.ux.json"]
            w["request"] = ""
        if w["id"] in {"proto_build", "boil_bench"}:
            w["status"] = "done"
            w["artifacts"] = ["bench/boil.csv"]
    plan["decisions"][0].update(status="decided", decision="local mill")
    (workspace / "bench").mkdir(exist_ok=True)
    (workspace / "bench" / "boil.csv").write_text("t_s,temp_c\n0,20\n240,100\n", encoding="utf-8")
    return plan


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    shutil.copytree(PRODUCT, tmp_path / "ws")
    return tmp_path / "ws"


def test_evaluation_done_without_evidence_fails(plan_dict: dict[str, Any], workspace: Path) -> None:
    plan = _evaluated(plan_dict, workspace)
    statuses = _statuses(plan, workspace)
    assert statuses["production.evidence_loop"] == "fail"


def test_evidence_feeds_revision(plan_dict: dict[str, Any], workspace: Path) -> None:
    plan = _evaluated(plan_dict, workspace)
    plan["evidence"] = [
        {
            "id": "done_cue_quiet",
            "workstream": "boil_bench",
            "observation": "done cue inaudible at 3 m with the tap running",
            "source": "bench/boil.csv",
            "feeds": ["rev_b_plan"],
        }
    ]
    report = run_production_gates(
        ProductionPlan.model_validate(plan), workspace, workspace / "requests"
    )
    assert report.verdict == "pass", [c for c in report.checks if c.status != "pass"]
    status = production_status(
        ProductionPlan.model_validate(plan), report, workspace, workspace / "requests"
    )
    assert status["current_stage"] == "manufacturing_handoff"  # user_manual still todo
    assert [a["id"] for a in status["next_actions"]] == ["user_manual", "rev_b_plan"]  # type: ignore[index]


def test_evidence_must_feed_design_or_revision(plan_dict: dict[str, Any], workspace: Path) -> None:
    plan = _evaluated(plan_dict, workspace)
    plan["evidence"] = [
        {
            "id": "x",
            "workstream": "boil_bench",
            "observation": "o",
            "source": "bench/boil.csv",
            "feeds": ["proto_build"],
        }
    ]
    assert _statuses(plan, workspace)["production.evidence_loop"] == "fail"


def test_evidence_source_must_exist(plan_dict: dict[str, Any], workspace: Path) -> None:
    plan = _evaluated(plan_dict, workspace)
    plan["evidence"] = [
        {
            "id": "x",
            "workstream": "boil_bench",
            "observation": "o",
            "source": "bench/missing.csv",
            "feeds": ["rev_b_plan"],
        }
    ]
    assert _statuses(plan, workspace)["production.evidence_loop"] == "fail"


def test_failing_ux_contract_fails_when_ux_done(plan_dict: dict[str, Any], workspace: Path) -> None:
    contract = json.loads((workspace / "smart-kettle.ux.json").read_text(encoding="utf-8"))
    contract["content"] = [a for a in contract["content"] if a["feedback"] != "app_reminder"]
    (workspace / "smart-kettle.ux.json").write_text(json.dumps(contract), encoding="utf-8")
    assert _statuses(plan_dict, workspace)["production.ux_contract"] == "fail"
    _ws(plan_dict, "ux_contract")["status"] = "in_progress"
    for w in plan_dict["workstreams"]:
        if w["id"] == "sound_cues":
            w["status"] = "todo"
    assert _statuses(plan_dict, workspace)["production.ux_contract"] == "unknown"


def test_missing_contract_is_unknown(plan_dict: dict[str, Any]) -> None:
    plan_dict["contract"] = "nope.ux.json"
    assert _statuses(plan_dict)["production.ux_contract"] == "unknown"


def test_cli_produce(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ux_creator.cli",
            "produce",
            str(PLAN),
            "--out",
            str(tmp_path),
            "--workspace",
            str(PRODUCT),
            "--liaison-dir",
            str(PRODUCT / "requests"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["verdict"] == "pass"
    assert payload["plan"]["sha256"].startswith("sha256:")
    assert (tmp_path / "smart-kettle.production-status.md").is_file()


def test_cli_produce_render_returns_rendered_plan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_render_all(out_dir: Path, **_kwargs: object) -> list[RenderResult]:
        assert _kwargs == {"fmts": ("svg", "png")}
        image = out_dir / "smart-kettle.production.png"
        image.write_bytes(b"rendered-plan")
        return [RenderResult(out_dir / "smart-kettle.production.mmd", image, "ok", "")]

    monkeypatch.setattr(cli, "render_all", fake_render_all)

    result = cli.main(
        [
            "produce",
            str(PLAN),
            "--out",
            str(tmp_path),
            "--workspace",
            str(PRODUCT),
            "--liaison-dir",
            str(PRODUCT / "requests"),
            "--render",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["renders"] == [
        {
            "source": str(tmp_path / "smart-kettle.production.mmd"),
            "output": str(tmp_path / "smart-kettle.production.png"),
            "status": "ok",
            "detail": "",
        }
    ]


def test_cli_produce_fails_closed_without_liaison(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ux_creator.cli",
            "produce",
            str(PLAN),
            "--out",
            str(tmp_path),
            "--workspace",
            str(PRODUCT),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["verdict"] == "fail"
