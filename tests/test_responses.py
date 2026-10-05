"""SLP v2 response validation and liaison reconciliation tests."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

import pytest
from pydantic import ValidationError

from ux_creator.contract import load_contract
from ux_creator.gates import run_gates
from ux_creator.records import tree_sha256
from ux_creator.report import build_report
from ux_creator.requests import UXRequest, build_request, write_request
from ux_creator.responses import (
    ArtifactRef,
    GateVerdict,
    LiaisonEntry,
    LiaisonStatus,
    ResponseStatus,
    UXResponse,
    liaison_status,
)
from ux_creator.sisters import ProductStage, TargetAgent

CONTRACT = Path(__file__).resolve().parents[1] / "examples/smart-kettle/smart-kettle.ux.json"
FIXED = datetime(2025, 1, 1, tzinfo=UTC)


def _request(
    directory: Path,
    request_id: str,
    target: str,
    *,
    risk: str = "low",
    depends_on: list[str] | None = None,
    inputs: list[str] | None = None,
) -> UXRequest:
    contract = load_contract(CONTRACT)
    rationale = "job boil supports the requested change" if risk == "high" else ""
    request = build_request(
        contract,
        id=request_id,
        target_agent=cast(TargetAgent, target),
        stage=cast(ProductStage, "design"),
        risk=cast(Literal["low", "high"], risk),
        purpose=f"Coordinate {request_id} with its sister agent",
        rationale=rationale,
        requested_changes=["review the requested design change"],
        inputs=inputs or [],
        expected_deliverables=["updated design artifact"],
        acceptance=["deliverable satisfies the requested change"],
        depends_on=depends_on or [],
        workspace=directory,
        now=FIXED,
    )
    write_request(request, directory)
    return request


def _response(
    directory: Path,
    request_id: str,
    responder: str,
    *,
    status: str = "accepted",
    input_hashes: dict[str, str] | None = None,
    artifacts: list[dict[str, str]] | None = None,
    decision_refs: list[str] | None = None,
    impression_refs: list[str] | None = None,
    questions_for_user: list[str] | None = None,
) -> Path:
    response = UXResponse(
        request=request_id,
        responder=cast(TargetAgent, responder),
        status=cast(ResponseStatus, status),
        reason="The requested design work has a clear outcome.",
        input_hashes=input_hashes or {},
        artifacts=[ArtifactRef.model_validate(artifact) for artifact in artifacts or []],
        decision_refs=decision_refs or [],
        impression_refs=impression_refs or [],
        questions_for_user=questions_for_user or [],
        responded_at=FIXED.isoformat(),
    )
    path = directory / f"{request_id}.ux-response.json"
    path.write_text(
        json.dumps(response.model_dump(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _entry(status: LiaisonStatus, request_id: str) -> LiaisonEntry:
    return next(entry for entry in status.entries if entry.request == request_id)


def test_answered_open_mismatched_and_orphan(tmp_path: Path) -> None:
    _request(tmp_path, "answered-one", "circuit")
    _response(tmp_path, "answered-one", "circuit")
    _request(tmp_path, "open-one", "mech")
    _request(tmp_path, "mismatch-one", "mech")
    _response(tmp_path, "mismatch-one", "wire")
    _response(tmp_path, "orphan-one", "sim")

    status = liaison_status(tmp_path, tmp_path)
    assert {entry.request: entry.state for entry in status.entries} == {
        "answered-one": "answered",
        "mismatch-one": "mismatched",
        "open-one": "open",
    }
    assert _entry(status, "answered-one").response_status == "accepted"
    assert "does not match target" in " ".join(_entry(status, "mismatch-one").problems)
    assert len(status.orphans) == 1 and "orphan-one" in status.orphans[0]
    assert status.summary["answered"] == 1
    assert status.summary["open"] == 1
    assert status.summary["mismatched"] == 1


def test_stale_input_hash_and_changed_input(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("original", encoding="utf-8")
    request = _request(tmp_path, "stale-one", "bard", inputs=["input.txt"])
    _response(
        tmp_path,
        request.id,
        "bard",
        input_hashes={"input.txt": request.inputs[0].sha256},
    )
    source.write_text("changed", encoding="utf-8")

    entry = _entry(liaison_status(tmp_path, tmp_path), request.id)
    assert entry.state == "stale"
    assert any("missing or changed" in problem for problem in entry.problems)


def test_broken_artifact_and_decision_reference(tmp_path: Path) -> None:
    _request(tmp_path, "missing-artifact", "firmware")
    _response(
        tmp_path,
        "missing-artifact",
        "firmware",
        status="done",
        artifacts=[{"path": "missing.bin", "sha256": "0" * 64}],
    )
    _request(tmp_path, "missing-decision", "doc")
    _response(
        tmp_path,
        "missing-decision",
        "doc",
        status="in_progress",
        decision_refs=["1" * 64],
    )
    status = liaison_status(tmp_path, tmp_path)
    assert _entry(status, "missing-artifact").state == "broken"
    assert (
        "artifact missing.bin is missing or changed" in _entry(status, "missing-artifact").problems
    )
    assert _entry(status, "missing-decision").state == "broken"
    assert "decision refs not found" in " ".join(_entry(status, "missing-decision").problems)


def test_cycles_blocked_open_and_malformed_files(tmp_path: Path) -> None:
    _request(tmp_path, "doc-cycle", "doc", depends_on=["fpga-cycle"])
    _request(tmp_path, "fpga-cycle", "fpga", depends_on=["doc-cycle"])
    _request(tmp_path, "blocked-one", "dashboard", depends_on=["doc-cycle"])
    _request(tmp_path, "unknown-dependency", "prodeng", depends_on=["missing-id"])
    _request(tmp_path, "plain-open", "sim")
    _request(tmp_path, "bad-response", "wire")
    (tmp_path / "bad-response.ux-response.json").write_text("{oops", encoding="utf-8")
    _request(tmp_path, "bad-done", "circuit")
    (tmp_path / "bad-done.ux-response.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "system": "ux-creator",
                "request": "bad-done",
                "responder": "circuit",
                "status": "done",
                "reason": "This response must be rejected by the schema.",
                "input_hashes": {},
                "artifacts": [],
                "gate_verdicts": [{"gate": "hardware", "verdict": "fail"}],
                "decision_refs": [],
                "impression_refs": [],
                "questions_for_user": [],
                "responded_at": FIXED.isoformat(),
            }
        ),
        encoding="utf-8",
    )

    status = liaison_status(tmp_path, tmp_path)
    assert _entry(status, "doc-cycle").state == "circular"
    assert _entry(status, "fpga-cycle").state == "circular"
    assert _entry(status, "blocked-one").state == "blocked"
    assert any(
        "dependency doc-cycle is circular" in problem
        for problem in _entry(status, "blocked-one").problems
    )
    assert _entry(status, "unknown-dependency").state == "blocked"
    assert _entry(status, "plain-open").state == "open"
    assert "bad-response" in " ".join(status.malformed)
    assert "bad-done" in " ".join(status.malformed)
    assert "response file is malformed" in " ".join(_entry(status, "bad-done").problems)
    assert status.summary["circular"] == 2
    assert status.summary["blocked"] == 2


def test_response_schema_rejects_short_reason_and_done_failure(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="reason"):
        UXResponse(
            request="short-reason",
            responder="doc",
            status="rejected",
            reason="no",
            responded_at=FIXED.isoformat(),
        )
    with pytest.raises(ValidationError, match="done responses"):
        UXResponse(
            request="done-failure",
            responder="doc",
            status="done",
            reason="The work failed its required gate.",
            gate_verdicts=[GateVerdict(gate="docs", verdict="unknown")],
            responded_at=FIXED.isoformat(),
        )
    with pytest.raises(ValidationError, match="timezone"):
        UXResponse(
            request="naive-response",
            responder="doc",
            status="accepted",
            responded_at="2025-01-01T00:00:00",
        )


def test_malformed_request_and_symlink_are_reported(tmp_path: Path) -> None:
    (tmp_path / "bad.ux-request.json").write_text("[]", encoding="utf-8")
    status = liaison_status(tmp_path, tmp_path)
    assert len(status.malformed) == 1
    assert status.malformed[0].startswith(f"{tmp_path / 'bad.ux-request.json'}: ")
    assert "UXRequest" in status.malformed[0]
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "linked.ux-request.json").symlink_to(outside)
    status = liaison_status(tmp_path, tmp_path)
    assert any("symlink" in item for item in status.malformed)


def test_liaison_lens_has_all_state_and_status_counts(
    tmp_path: Path,
) -> None:
    contract = load_contract(CONTRACT)
    report = run_gates(contract, tmp_path)
    _request(tmp_path, "question-one", "bard")
    _response(
        tmp_path,
        "question-one",
        "bard",
        status="needs_info",
        questions_for_user=["Which cue should be prioritized?"],
    )
    lens = build_report(contract, report, out_dir=tmp_path)["lenses"]["liaison"]
    assert set(lens["by_state"]) == {
        "open",
        "answered",
        "mismatched",
        "stale",
        "broken",
        "blocked",
        "circular",
    }
    assert set(lens["by_status"]) == {
        "accepted",
        "in_progress",
        "done",
        "rejected",
        "deferred",
        "needs_info",
    }
    assert lens["by_status"]["needs_info"] == 1
    assert lens["open_user_questions"] == 1


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ux_creator", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_liaison_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    _request(tmp_path / "liaison", "cli-one", "circuit")
    _response(tmp_path / "liaison", "cli-one", "circuit", status="deferred")
    proc = _run(
        "liaison",
        "--workspace",
        str(tmp_path),
        "--liaison-dir",
        "liaison",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["verdict"] == "pass"
    assert payload["stage"] == "liaison"
    assert payload["entries"][0]["state"] == "answered"
    assert payload["entries"][0]["response_status"] == "deferred"


def test_tree_hash_matches_request_input_reference(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("bound input", encoding="utf-8")
    request = _request(tmp_path, "hash-one", "mech", inputs=["input.txt"])
    assert request.inputs[0].sha256 == tree_sha256(source)
