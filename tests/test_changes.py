from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from ux_creator import cli
from ux_creator.changes import check_eco, pins
from ux_creator.mcp_server import dispatch_tool

NOW = "2026-10-11T00:00:00+00:00"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return _sha(path)


def _workspace(tmp_path: Path, **eco: Any) -> Path:
    """circuit board.json v1 -> v2; mech brief.json re-pins it; both gated."""
    board = tmp_path / "circuit/board.json"
    old_board = _write(board, {"width_mm": 20})
    brief = tmp_path / "mech/brief.json"
    old_brief = _write(brief, {"board": {"path": "../circuit/board.json", "sha256": old_board}})
    ecr = tmp_path / "changes/ECR-1.ecr.json"
    _write(
        ecr,
        {
            "schema_version": "vibebb.ecr/v1",
            "id": "ECR-1",
            "origin": "circuit",
            "reason": "the board must widen for a connector",
            "proposal": "widen the board to 24 mm",
            "items": [{"path": "circuit/board.json", "sha256": old_board}],
            "created_at": NOW,
            **eco.pop("ecr_extra", {}),
        },
    )
    new_board = _write(board, {"width_mm": 24})
    pinned = eco.pop("pinned", new_board)
    new_brief = _write(brief, {"board": {"path": "../circuit/board.json", "sha256": pinned}})
    reports = {
        "circuit": _write(tmp_path / "circuit/gates.json", {"verdict": "pass", "src": new_board}),
        "mech": _write(tmp_path / "mech/gates.json", {"verdict": "pass", "brief": new_brief}),
    }
    changes = [
        {
            "path": "circuit/board.json",
            "before": old_board,
            "after": new_board,
            "gate_report": {"path": "circuit/gates.json", "sha256": reports["circuit"]},
        },
        {
            "path": "mech/brief.json",
            "before": old_brief,
            "after": new_brief,
            "gate_report": {"path": "mech/gates.json", "sha256": reports["mech"]},
        },
    ]
    record: dict[str, Any] = {
        "schema_version": "vibebb.eco/v1",
        "id": "ECO-1",
        "ecr": {"path": "changes/ECR-1.ecr.json", "sha256": _sha(ecr)},
        "author": "circuit",
        "changes": changes[: eco.pop("keep", 2)],
        "review": {
            "reviewers": ["mech-review"],
            "findings": [
                {
                    "id": "F1",
                    "reviewer": "mech-review",
                    "severity": "minor",
                    "subject": "mech/brief.json",
                    "text": "clearance to the wall is tight",
                    "disposition": "accepted",
                    "resolution": "0.5 mm still meets the fit gate",
                }
            ],
        },
        "created_at": NOW,
    }
    record.update(eco)
    _write(tmp_path / "changes/ECO-1.eco.json", record)
    return tmp_path / "changes/ECO-1.eco.json"


def _failed(report: dict[str, Any]) -> set[str]:
    return {c["id"] for c in report["checks"] if c["status"] != "pass"}


def test_closed_change_passes(tmp_path: Path) -> None:
    report = check_eco(_workspace(tmp_path), tmp_path)
    assert report["verdict"] == "pass", report
    assert ("mech/brief.json", "circuit/board.json") in {(c, t) for c, t, _ in pins(tmp_path)}


def test_stale_consumer_pin_fails(tmp_path: Path) -> None:
    report = check_eco(_workspace(tmp_path, pinned="0" * 64), tmp_path)
    assert report["verdict"] == "fail"
    assert "eco.pins" in _failed(report)


def test_unlisted_impacted_consumer_fails(tmp_path: Path) -> None:
    report = check_eco(_workspace(tmp_path, keep=1), tmp_path)
    assert _failed(report) == {"eco.pins"}


def test_gate_report_without_after_sha_is_unknown(tmp_path: Path) -> None:
    eco = _workspace(tmp_path)
    report_path = tmp_path / "mech/gates.json"
    record = json.loads(eco.read_text(encoding="utf-8"))
    record["changes"][1]["gate_report"]["sha256"] = _write(report_path, {"verdict": "pass"})
    _write(eco, record)
    statuses = {
        c["status"] for c in check_eco(eco, tmp_path)["checks"] if c["id"] == "eco.evidence"
    }
    assert "unknown" in statuses
    assert check_eco(eco, tmp_path)["verdict"] == "fail"


@pytest.mark.parametrize("verdict", ["fail", "unknown", None])
def test_unpassed_gate_report_fails(tmp_path: Path, verdict: str | None) -> None:
    eco = _workspace(tmp_path)
    record = json.loads(eco.read_text(encoding="utf-8"))
    after = record["changes"][0]["after"]
    sha = _write(tmp_path / "circuit/gates.json", {"verdict": verdict, "src": after})
    record["changes"][0]["gate_report"]["sha256"] = sha
    _write(eco, record)
    assert "eco.evidence" in _failed(check_eco(eco, tmp_path))


def test_changed_gate_report_and_ecr_fail(tmp_path: Path) -> None:
    eco = _workspace(tmp_path)
    _write(tmp_path / "circuit/gates.json", {"verdict": "pass"})
    (tmp_path / "changes/ECR-1.ecr.json").write_text("{}", encoding="utf-8")
    failed = _failed(check_eco(eco, tmp_path))
    assert {"eco.evidence", "eco.ecr"} <= failed


def test_unapplied_change_fails(tmp_path: Path) -> None:
    eco = _workspace(tmp_path)
    _write(tmp_path / "circuit/board.json", {"width_mm": 25})
    assert "eco.applied" in _failed(check_eco(eco, tmp_path))


def test_ecr_item_left_out_fails(tmp_path: Path) -> None:
    extra = {"items": [{"path": "circuit/board.json", "sha256": "1" * 64}]}
    report = check_eco(_workspace(tmp_path, ecr_extra=extra), tmp_path)
    assert "eco.scope" in _failed(report)


def test_self_review_fails(tmp_path: Path) -> None:
    review = {"reviewers": ["circuit"], "findings": []}
    assert _failed(check_eco(_workspace(tmp_path, review=review), tmp_path)) == {"dr.independence"}


@pytest.mark.parametrize(
    ("severity", "disposition", "resolution", "reviewer"),
    [
        ("minor", "open", "will look at it later", "mech-review"),
        ("blocker", "accepted", "we can live with this", "mech-review"),
        ("major", "fixed", "", "mech-review"),
        ("minor", "fixed", "widened the wall gap", "stranger"),
    ],
)
def test_unresolved_findings_fail(
    tmp_path: Path, severity: str, disposition: str, resolution: str, reviewer: str
) -> None:
    finding = {
        "id": "F1",
        "reviewer": reviewer,
        "severity": severity,
        "subject": "mech/brief.json",
        "text": "connector overlaps the boss",
        "disposition": disposition,
        "resolution": resolution,
    }
    review = {"reviewers": ["mech-review"], "findings": [finding]}
    assert _failed(check_eco(_workspace(tmp_path, review=review), tmp_path)) == {"dr.findings"}


def test_change_cycle_fails(tmp_path: Path) -> None:
    eco = _workspace(tmp_path, ecr_extra={"raised_by": "ECO-1"})
    assert "eco.cycle" in _failed(check_eco(eco, tmp_path))


def test_malformed_eco_fails(tmp_path: Path) -> None:
    eco = tmp_path / "bad.eco.json"
    eco.write_text('{"schema_version": "vibebb.eco/v1"}', encoding="utf-8")
    report = check_eco(eco, tmp_path)
    assert report["verdict"] == "fail"
    assert _failed(report) == {"eco.record"}


def test_cli_and_mcp_report_the_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    eco = _workspace(tmp_path)
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert cli.main(["change", str(eco), "--workspace", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "pass"
    payload = asyncio.run(
        dispatch_tool("ux_change_check", {"eco_path": str(eco), "workspace": str(tmp_path)})
    )
    assert isinstance(payload, dict) and payload["verdict"] == "pass"
    _write(tmp_path / "circuit/board.json", {"width_mm": 30})
    assert cli.main(["change", str(eco), "--workspace", str(tmp_path)]) == 1


@pytest.mark.parametrize(("length", "status"), [(11, "fail"), (12, "pass"), (13, "pass")])
def test_resolution_length_boundary(tmp_path: Path, length: int, status: str) -> None:
    finding = {
        "id": "F1",
        "reviewer": "mech-review",
        "severity": "major",
        "subject": "mech/brief.json",
        "text": "connector overlaps the boss",
        "disposition": "accepted",
        "resolution": "x" * length,
    }
    review = {"reviewers": ["mech-review"], "findings": [finding]}
    report = check_eco(_workspace(tmp_path, review=review), tmp_path)
    assert {c["status"] for c in report["checks"] if c["id"] == "dr.findings"} == {status}


def test_missing_inputs_fail_closed(tmp_path: Path) -> None:
    eco = _workspace(tmp_path)
    (tmp_path / "mech/gates.json").unlink()
    (tmp_path / "circuit/board.json").unlink()
    report = check_eco(eco, tmp_path)
    statuses = {(c["id"], c["status"]) for c in report["checks"]}
    assert ("eco.evidence", "unknown") in statuses
    assert ("eco.applied", "fail") in statuses
    (tmp_path / "changes/ECR-1.ecr.json").unlink()
    statuses = {(c["id"], c["status"]) for c in check_eco(eco, tmp_path)["checks"]}
    assert ("eco.ecr", "unknown") in statuses


def test_non_object_gate_report_fails(tmp_path: Path) -> None:
    eco = _workspace(tmp_path)
    record = json.loads(eco.read_text(encoding="utf-8"))
    record["changes"][0]["gate_report"]["sha256"] = _write(tmp_path / "circuit/gates.json", [])
    _write(eco, record)
    assert "eco.evidence" in _failed(check_eco(eco, tmp_path))


@pytest.mark.parametrize("field", ["changes", "findings"])
def test_duplicate_entries_are_rejected(tmp_path: Path, field: str) -> None:
    eco = _workspace(tmp_path)
    record = json.loads(eco.read_text(encoding="utf-8"))
    target = record["changes"] if field == "changes" else record["review"]["findings"]
    target.append(target[0])
    _write(eco, record)
    assert _failed(check_eco(eco, tmp_path)) == {"eco.record"}


def test_pins_ignore_skipped_dirs_and_outside_paths(tmp_path: Path) -> None:
    _workspace(tmp_path)
    sha = _sha(tmp_path / "circuit/board.json")
    _write(tmp_path / "out/copy.json", {"path": "../circuit/board.json", "sha256": sha})
    _write(tmp_path / "mech/escape.json", {"path": "../../etc/passwd", "sha256": sha})
    consumers = {consumer for consumer, _, _ in pins(tmp_path)}
    assert "out/copy.json" not in consumers
    assert "mech/escape.json" not in consumers
