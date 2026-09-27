"""Phase-3 tests: richer statecharts, feedback/loop gates, game-design lens."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

from ux_creator.contract import UXContract
from ux_creator.gates import run_gates
from ux_creator.projections import write_projections
from ux_creator.report import build_report


def _contract(payload: dict[str, Any]) -> UXContract:
    return UXContract.model_validate(payload)


def _check(report: Any, check_id: str) -> Any:
    return next(c for c in report.checks if c.id == check_id)


def test_state_surface_ok(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["statecharts"][0]["states"][0]["surface"] = "btn"
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "statechart.sc.state_surface_declared").status == "pass"


def test_state_surface_undeclared_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["statecharts"][0]["states"][0]["surface"] = "ghost"
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "statechart.sc.state_surface_declared").status == "fail"


def test_deterministic_duplicate_unguarded_fails(
    contract_dict: dict[str, Any], tmp_path: Path
) -> None:
    contract_dict["statecharts"][0]["transitions"].append({"from": "a", "event": "go", "to": "a"})
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "statechart.sc.deterministic").status == "fail"


def test_deterministic_distinct_guards_pass(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["statecharts"][0]["states"].append({"id": "c", "final": True})
    contract_dict["statecharts"][0]["transitions"] = [
        {"from": "a", "event": "go", "to": "b", "guard": "x > 1"},
        {"from": "a", "event": "go", "to": "c", "guard": "x <= 1"},
    ]
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "statechart.sc.deterministic").status == "pass"


def test_deterministic_same_guard_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["statecharts"][0]["transitions"] = [
        {"from": "a", "event": "go", "to": "b", "guard": "same"},
        {"from": "a", "event": "go", "to": "b", "guard": "same"},
    ]
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "statechart.sc.deterministic").status == "fail"


def _feedback(contract_dict: dict[str, Any], **kw: Any) -> None:
    entry: dict[str, Any] = {
        "id": "fb1",
        "trigger": "go",
        "surface": "btn",
        "modality": "visual",
        "latency_ms": 50,
    }
    entry.update(kw)
    contract_dict["feedback"] = [entry]


def test_feedback_surface_undeclared_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    _feedback(contract_dict, surface="ghost")
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "feedback.surface_declared").status == "fail"


def test_feedback_trigger_unknown_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    _feedback(contract_dict, trigger="nonexistent")
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "feedback.trigger_known").status == "fail"


def test_feedback_trigger_touchpoint_ok(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    _feedback(contract_dict, trigger="btn")
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "feedback.trigger_known").status == "pass"


def test_feedback_3000ms_without_indicator_fails(
    contract_dict: dict[str, Any], tmp_path: Path
) -> None:
    _feedback(contract_dict, latency_ms=3000)
    report = run_gates(_contract(contract_dict), tmp_path)
    check = _check(report, "feedback.latency_budget")
    assert check.status == "fail"
    assert check.measured == 3000.0 and check.limit == 10000.0


def test_feedback_3000ms_with_indicator_passes(
    contract_dict: dict[str, Any], tmp_path: Path
) -> None:
    _feedback(contract_dict, latency_ms=3000, progress_indicator=True)
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "feedback.latency_budget").status == "pass"


def test_feedback_20000ms_always_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    _feedback(contract_dict, latency_ms=20000, progress_indicator=True)
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "feedback.latency_budget").status == "fail"


def test_loop_unknown_step_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["loops"] = [{"id": "l1", "steps": ["go", "teleport"], "cadence": "daily"}]
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "loop.steps_known").status == "fail"


def test_loop_session_without_reward_fails(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["loops"] = [{"id": "l1", "steps": ["go"], "cadence": "session"}]
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "loop.closes").status == "fail"


def test_loop_daily_without_reward_ok(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["loops"] = [{"id": "l1", "steps": ["go"], "cadence": "daily"}]
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "loop.closes").status == "pass"


def test_onboarding_required_for_app_surface(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["product"]["surfaces"].append({"id": "app", "layer": "smartphone_app"})
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "journey.onboarding_present").status == "fail"


def test_onboarding_stage_satisfies_gate(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract_dict["product"]["surfaces"].append({"id": "app", "layer": "smartphone_app"})
    contract_dict["journeys"][0]["stages"].append({"id": "ob", "kind": "onboard", "emotion": 3})
    report = run_gates(_contract(contract_dict), tmp_path)
    assert _check(report, "journey.onboarding_present").status == "pass"


def test_hardware_only_exempt(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    report = run_gates(_contract(contract_dict), tmp_path)
    assert all(c.id != "journey.onboarding_present" for c in report.checks)


def test_example_contract_still_passes(tmp_path: Path) -> None:
    example = json.loads(
        Path("examples/smart-kettle/smart-kettle.ux.json").read_text(encoding="utf-8")
    )
    report = run_gates(UXContract.model_validate(example), tmp_path)
    assert report.verdict == "pass"
    assert _check(report, "statechart.power.deterministic").status == "pass"


def test_xstate_guarded_transitions(tmp_path: Path) -> None:
    example = json.loads(
        Path("examples/smart-kettle/smart-kettle.ux.json").read_text(encoding="utf-8")
    )
    contract = UXContract.model_validate(example)
    paths = write_projections(contract, "x", tmp_path)
    machine = json.loads(paths["x.power.xstate.json"].read_text(encoding="utf-8"))
    on = machine["states"]["heating"]["on"]["boiled"]
    assert isinstance(on, list)
    entries = cast(list[dict[str, object]], on)
    assert len(entries) == 2
    assert {str(e["guard"]) for e in entries} == {"temp >= 100", "keep_warm_armed"}
    assert machine["states"]["heating"]["entry"] == ["led_pulse"]
    assert machine["states"]["heating"]["meta"] == {"surface": "status_led"}
    assert machine["states"]["heating"]["description"].startswith("water heating")


def test_scxml_cond_and_actions(tmp_path: Path) -> None:
    example = json.loads(
        Path("examples/smart-kettle/smart-kettle.ux.json").read_text(encoding="utf-8")
    )
    contract = UXContract.model_validate(example)
    write_projections(contract, "x", tmp_path)
    text = (tmp_path / "x.power.scxml").read_text(encoding="utf-8")
    assert 'cond="temp &gt;= 100"' in text or 'cond="temp >= 100"' in text
    assert '<log label="action"' in text
    assert "<onentry>" in text


def test_stories_include_states_and_feedback(tmp_path: Path) -> None:
    example = json.loads(
        Path("examples/smart-kettle/smart-kettle.ux.json").read_text(encoding="utf-8")
    )
    contract = UXContract.model_validate(example)
    write_projections(contract, "x", tmp_path)
    data = json.loads((tmp_path / "x.stories.json").read_text(encoding="utf-8"))
    led = next(s for s in data["stories"] if s["surface"] == "status_led")
    assert led["states"] == ["heating", "keep_warm"]
    assert "heating" in led["required_stories"]
    assert led["feedback"] == ["led_boiling"]
    app = next(s for s in data["stories"] if s["surface"] == "mobile_app")
    assert app["feedback"] == ["app_reminder"]


def test_experience_loops_mmd_in_manifest(tmp_path: Path) -> None:
    example = json.loads(
        Path("examples/smart-kettle/smart-kettle.ux.json").read_text(encoding="utf-8")
    )
    contract = UXContract.model_validate(example)
    paths = write_projections(contract, "x", tmp_path)
    assert "x.experience-loops.mmd" in paths
    text = paths["x.experience-loops.mmd"].read_text(encoding="utf-8")
    assert "flowchart LR" in text and "morning_brew" in text
    manifest = json.loads(paths["manifest.json"].read_text(encoding="utf-8"))
    assert "x.experience-loops.mmd" in {a["path"] for a in manifest["artifacts"]}


def test_report_game_design_lens(tmp_path: Path) -> None:
    example = json.loads(
        Path("examples/smart-kettle/smart-kettle.ux.json").read_text(encoding="utf-8")
    )
    contract = UXContract.model_validate(example)
    report = build_report(contract, run_gates(contract, tmp_path))
    lens = report["lenses"]["game_design"]
    assert lens["loops"] == 1
    assert lens["feedback_count"] == 3
    assert lens["feedback_by_modality"] == {"audio": 1, "text": 1, "visual": 1}
    assert lens["avg_loop_length"] == 3
    assert lens["onboard_stages"] == 1
    assert "kettle_body" in lens["surfaces_without_feedback"]


def test_deepcopy_corruption_guards(contract_dict: dict[str, Any]) -> None:
    payload = copy.deepcopy(contract_dict)
    payload["feedback"] = [{"id": "f", "trigger": "?", "surface": "?", "modality": "x"}]
    try:
        UXContract.model_validate(payload)
        raised = False
    except Exception:
        raised = True
    assert raised
