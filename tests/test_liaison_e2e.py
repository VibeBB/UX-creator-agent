"""End-to-end SLP v2 fixture across liaison, production, CLI, and MCP."""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

import pytest

from ux_creator import mcp_server
from ux_creator.contract import load_contract
from ux_creator.observations import collect_records
from ux_creator.production import ProductionPlan, production_status, run_production_gates
from ux_creator.records import tree_sha256
from ux_creator.requests import UXRequest, build_request, write_request
from ux_creator.responses import (
    ArtifactRef,
    GateVerdict,
    ResponseStatus,
    UXResponse,
    liaison_status,
)
from ux_creator.sisters import ProductStage, TargetAgent

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "examples/smart-kettle/smart-kettle.ux.json"
FIXTURES = REPO_ROOT / "tests/fixtures/liaison"
FIXED = datetime(2025, 1, 1, tzinfo=UTC)


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    shutil.copyfile(CONTRACT, root / "smart-kettle.ux.json")
    shutil.copyfile(FIXTURES / "input.txt", root / "stale.txt")
    artifact = root / "deliverables" / "mech.txt"
    artifact.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURES / "mech.txt", artifact)
    return root


def _request(
    workspace: Path,
    request_id: str,
    target: str,
    *,
    risk: str = "low",
    depends_on: list[str] | None = None,
    inputs: list[str] | None = None,
) -> UXRequest:
    contract = load_contract(workspace / "smart-kettle.ux.json")
    rationale = "job boil supports the required change" if risk == "high" else ""
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
        workspace=workspace,
        now=FIXED,
    )
    write_request(request, workspace / "liaison")
    return request


def _response(
    workspace: Path,
    request: UXRequest | str,
    responder: str,
    *,
    status: str = "accepted",
    artifacts: list[dict[str, str]] | None = None,
    decision_refs: list[str] | None = None,
    impression_refs: list[str] | None = None,
    questions_for_user: list[str] | None = None,
    gate_verdicts: list[dict[str, str]] | None = None,
) -> UXResponse:
    request_id = request.id if isinstance(request, UXRequest) else request
    input_hashes = (
        {item.path: item.sha256 for item in request.inputs}
        if isinstance(request, UXRequest)
        else {}
    )
    response = UXResponse(
        request=request_id,
        responder=cast(TargetAgent, responder),
        status=cast(ResponseStatus, status),
        reason="The requested work has a clear and documented outcome.",
        input_hashes=input_hashes,
        artifacts=[ArtifactRef.model_validate(artifact) for artifact in artifacts or []],
        gate_verdicts=[GateVerdict.model_validate(verdict) for verdict in gate_verdicts or []],
        decision_refs=decision_refs or [],
        impression_refs=impression_refs or [],
        questions_for_user=questions_for_user or [],
        responded_at=FIXED.isoformat(),
    )
    path = workspace / "liaison" / f"{request_id}.ux-response.json"
    path.write_text(
        json.dumps(response.model_dump(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return response


def _append_vrp_event(workspace: Path, plugin: str, kind: str, body: dict[str, object]) -> str:
    filenames = {
        "decision": "decisions.jsonl",
        "stage_impression": "impressions.jsonl",
        "vision_review": "vision-reviews.jsonl",
    }
    directory = workspace / "observations" / plugin
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / filenames[kind]
    existing = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
    sequence = len([line for line in existing if line.strip()]) + 1
    identity = {"kind": kind, "sequence": sequence, **body}
    event_id = hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    event = {
        "schema_version": 1,
        "kind": kind,
        "plugin": plugin,
        "sequence": sequence,
        "event_id": event_id,
        "recorded_at": FIXED.isoformat(),
        **body,
    }
    with log.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    return event_id


def _plan(workspace: Path) -> ProductionPlan:
    path = workspace / "liaison-test.production.json"
    plan = {
        "schema_version": 1,
        "system": "ux-creator",
        "artifact_kind": "ux_production_plan",
        "product": "smart-kettle",
        "revision": "e2e",
        "goal": "Validate sister-agent collaboration from request through production status.",
        "contract": "smart-kettle.ux.json",
        "decisions": [
            {
                "id": "e2e_choice",
                "question": "Should the enclosure key move closer to the status light?",
                "options": ["keep current spacing", "move key closer"],
                "status": "open",
                "decision": "",
                "rationale": "",
                "blocks": [],
            }
        ],
        "workstreams": [
            {
                "id": "ux_contract",
                "stage": "requirements",
                "owner": "ux",
                "deliverable": "Validated UX contract",
                "status": "done",
                "artifacts": ["smart-kettle.ux.json"],
            },
            {
                "id": "mech_done",
                "stage": "design",
                "owner": "mech",
                "deliverable": "Completed enclosure update",
                "depends_on": ["ux_contract"],
                "status": "done",
                "artifacts": ["deliverables/mech.txt"],
                "request": "mech-done",
            },
            {
                "id": "bard_stale",
                "stage": "design",
                "owner": "bard",
                "deliverable": "Cue review from a stale source",
                "status": "in_progress",
                "request": "stale-bard",
            },
            {
                "id": "circuit_mismatch",
                "stage": "design",
                "owner": "circuit",
                "deliverable": "Circuit response reconciliation",
                "status": "todo",
                "request": "circuit-mismatch",
            },
            {
                "id": "firmware_broken",
                "stage": "design",
                "owner": "firmware",
                "deliverable": "Firmware artifact reconciliation",
                "status": "todo",
                "request": "broken-firmware",
            },
            {
                "id": "doc_broken",
                "stage": "design",
                "owner": "doc",
                "deliverable": "Decision evidence reconciliation",
                "status": "todo",
                "request": "doc-broken",
            },
            {
                "id": "doc_cycle",
                "stage": "design",
                "owner": "doc",
                "deliverable": "Documentation dependency",
                "status": "todo",
                "request": "doc-cycle",
            },
            {
                "id": "fpga_cycle",
                "stage": "design",
                "owner": "fpga",
                "deliverable": "FPGA dependency",
                "status": "todo",
                "request": "fpga-cycle",
            },
            {
                "id": "blocked_one",
                "stage": "design",
                "owner": "dashboard",
                "deliverable": "Work blocked by a stale request",
                "status": "todo",
                "request": "blocked-one",
            },
            {
                "id": "plain_open",
                "stage": "design",
                "owner": "sim",
                "deliverable": "Open simulation request",
                "status": "todo",
                "request": "plain-open",
            },
            {
                "id": "unknown_dependency",
                "stage": "design",
                "owner": "prodeng",
                "deliverable": "Request with an unknown dependency",
                "status": "todo",
                "request": "unknown-dependency",
            },
            {
                "id": "bad_response",
                "stage": "design",
                "owner": "wire",
                "deliverable": "Malformed response fixture",
                "status": "todo",
                "request": "bad-response",
            },
            {
                "id": "bad_done",
                "stage": "design",
                "owner": "circuit",
                "deliverable": "Invalid done response fixture",
                "status": "todo",
                "request": "bad-done",
            },
            {
                "id": "unlinked",
                "stage": "revision",
                "owner": "user",
                "deliverable": "Unlinked user-owned next step",
                "status": "todo",
            },
        ],
    }
    path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ProductionPlan.model_validate(plan)


def _populate_fixture(workspace: Path) -> ProductionPlan:
    (workspace / "liaison").mkdir(exist_ok=True)
    artifact = workspace / "deliverables" / "mech.txt"
    stable_input = workspace / "stale.txt"

    mech_request = _request(workspace, "mech-done", "mech", risk="high")
    stale_request = _request(workspace, "stale-bard", "bard", inputs=["stale.txt"])
    _request(workspace, "circuit-mismatch", "circuit")
    _request(workspace, "broken-firmware", "firmware")
    _request(workspace, "doc-broken", "doc")
    _request(workspace, "doc-cycle", "doc", depends_on=["fpga-cycle"])
    _request(workspace, "fpga-cycle", "fpga", depends_on=["doc-cycle"])
    _request(workspace, "blocked-one", "dashboard", depends_on=["stale-bard"])
    _request(workspace, "plain-open", "sim")
    _request(workspace, "unknown-dependency", "prodeng", depends_on=["missing-id"])
    _request(workspace, "bad-response", "wire")
    _request(workspace, "bad-done", "circuit")

    decision_body: dict[str, object] = {
        "id": "mech-key-location",
        "stage": "design",
        "question": "Which key location best supports blind use?",
        "principles": ["A tactile landmark must remain reachable without visual attention."],
        "options": [
            {
                "name": "raised",
                "pros": ["Easy to find by touch"],
                "cons": ["Slightly changes the top surface"],
            },
            {
                "name": "flush",
                "pros": ["Preserves the current top surface"],
                "cons": ["Harder to locate without looking"],
            },
        ],
        "chosen": "raised",
        "rationale": (
            "The raised key establishes a tactile landmark that can be found without "
            "requiring visual attention. It preserves clearance around the enclosure lip "
            "and makes the boil action easier to distinguish from adjacent controls."
        ),
        "assumptions": ["The molded cap can retain its current material."],
        "unknowns": ["The final glove thickness for the target user group."],
        "risks": ["The raised feature could collect debris during cleaning."],
        "revisit_when": "A washability test shows that the raised edge traps residue.",
        "decided_by": "agent",
        "evidence": [{"reference": "Mechanical enclosure review fixture"}],
    }
    decision_ref = _append_vrp_event(workspace, "mech", "decision", decision_body)
    impression_body: dict[str, object] = {
        "stage": "design",
        "artifacts": [{"path": "deliverables/mech.txt", "sha256": tree_sha256(artifact)}],
        "impression": (
            "The raised key creates a clear tactile landmark on the enclosure. Its position "
            "keeps the interaction distinct from the neighboring controls. The current "
            "artifact indicates adequate clearance around the lid seam. A gloved-hand check "
            "should confirm the key remains easy to locate. The next iteration should review "
            "cleanability and the visual relationship to the status light."
        ),
    }
    impression_ref = _append_vrp_event(workspace, "mech", "stage_impression", impression_body)
    _append_vrp_event(
        workspace,
        "mech",
        "vision_review",
        {
            "image_path": "deliverables/mech.txt",
            "findings": [{"severity": []}],
            "impression": "Malformed severity is safely summarized.",
        },
    )

    _response(
        workspace,
        mech_request,
        "mech",
        status="done",
        artifacts=[{"path": "deliverables/mech.txt", "sha256": tree_sha256(artifact)}],
        decision_refs=[decision_ref],
        impression_refs=[impression_ref],
        questions_for_user=["Should the raised key move closer to the status light?"],
        gate_verdicts=[{"gate": "enclosure-clearance", "verdict": "pass"}],
    )
    _response(
        workspace,
        stale_request,
        "bard",
    )
    stable_input.write_text("after revision\n", encoding="utf-8")
    _response(workspace, "circuit-mismatch", "wire")
    firmware_artifact = workspace / "deliverables" / "firmware.bin"
    firmware_artifact.write_text("firmware release e2e fixture\n", encoding="utf-8")
    _response(
        workspace,
        "broken-firmware",
        "firmware",
        artifacts=[
            {
                "path": "deliverables/firmware.bin",
                "sha256": tree_sha256(firmware_artifact),
            }
        ],
    )
    firmware_artifact.unlink()
    _response(
        workspace,
        "doc-broken",
        "doc",
        status="in_progress",
        decision_refs=["1" * 64],
    )
    _response(workspace, "orphan-one", "sim")

    (workspace / "liaison" / "bad-response.ux-response.json").write_text("{oops", encoding="utf-8")
    invalid_done = _response(
        workspace,
        "bad-done",
        "circuit",
        status="done",
        gate_verdicts=[{"gate": "fixture", "verdict": "pass"}],
    )
    invalid_payload = invalid_done.model_dump()
    invalid_payload["gate_verdicts"][0]["verdict"] = "fail"
    (workspace / "liaison" / "bad-done.ux-response.json").write_text(
        json.dumps(invalid_payload), encoding="utf-8"
    )
    (workspace / "liaison" / "broken-request.ux-request.json").write_text(
        "[not valid JSON]", encoding="utf-8"
    )
    return _plan(workspace)


def test_liaison_e2e(workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    plan = _populate_fixture(workspace)
    status = liaison_status(workspace / "liaison", workspace)

    assert {entry.request: entry.state for entry in status.entries} == {
        "bad-done": "open",
        "bad-response": "open",
        "blocked-one": "blocked",
        "broken-firmware": "broken",
        "circuit-mismatch": "mismatched",
        "doc-broken": "broken",
        "doc-cycle": "circular",
        "fpga-cycle": "circular",
        "mech-done": "answered",
        "plain-open": "open",
        "stale-bard": "stale",
        "unknown-dependency": "blocked",
    }
    assert len(status.orphans) == 1 and "orphan-one" in status.orphans[0]
    assert len(status.malformed) == 3
    assert status.summary == {
        "open": 3,
        "answered": 1,
        "mismatched": 1,
        "stale": 1,
        "broken": 2,
        "blocked": 2,
        "circular": 2,
    }
    assert "input stale.txt is missing or changed" in " ".join(
        next(entry for entry in status.entries if entry.request == "stale-bard").problems
    )
    assert "does not match target circuit" in " ".join(
        next(entry for entry in status.entries if entry.request == "circuit-mismatch").problems
    )
    assert "decision refs not found" in " ".join(
        next(entry for entry in status.entries if entry.request == "doc-broken").problems
    )
    assert "dependency stale-bard is stale" in " ".join(
        next(entry for entry in status.entries if entry.request == "blocked-one").problems
    )
    assert "dependency missing-id does not exist" in " ".join(
        next(entry for entry in status.entries if entry.request == "unknown-dependency").problems
    )

    report = run_production_gates(plan, workspace, workspace / "liaison")
    gates = {check.id: check.status for check in report.checks}
    assert gates["production.requests_answered"] == "pass"
    assert gates["production.request_owner"] == "pass"
    assert gates["production.liaison_integrity"] == "fail"
    assert gates["production.sister_records"] == "pass"

    focused_data = plan.model_dump()
    focused_data["contract"] = ""
    focused_data["workstreams"] = focused_data["workstreams"][:2]
    focused_plan = ProductionPlan.model_validate(focused_data)
    focused_liaison = workspace / "focused-liaison"
    focused_liaison.mkdir()
    for suffix in (".ux-request.json", ".ux-response.json"):
        shutil.copyfile(
            workspace / "liaison" / f"mech-done{suffix}",
            focused_liaison / f"mech-done{suffix}",
        )
    focused_report = run_production_gates(focused_plan, workspace, focused_liaison)
    focused_gates = {check.id: check.status for check in focused_report.checks}
    assert focused_gates["production.requests_answered"] == "pass"
    assert focused_gates["production.request_owner"] == "pass"
    assert focused_gates["production.liaison_integrity"] == "pass"
    assert focused_gates["production.sister_records"] == "pass"

    projected = production_status(plan, report, workspace, workspace / "liaison")
    questions = cast(list[dict[str, object]], projected["open_user_questions"])
    assert any(question["request"] == "mech-done" for question in questions)
    liaison_rows = cast(list[dict[str, object]], projected["liaison"])
    links = {row["workstream"]: row for row in liaison_rows}
    assert links["unlinked"]["state"] == "unlinked"
    assert links["doc_cycle"]["state"] == "circular"
    sister_projection = cast(dict[str, dict[str, object]], projected["sister_records"])
    assert sister_projection["mech"]["counts"] == {
        "decisions": 1,
        "impressions": 1,
        "vision_reviews": 1,
    }
    projected_impressions = cast(
        list[dict[str, object]], sister_projection["mech"]["latest_impressions"]
    )
    assert projected_impressions[0]["fresh"] is True
    records = collect_records(workspace)
    mech = records["mech"]
    assert mech.counts == {"decisions": 1, "impressions": 1, "vision_reviews": 1}
    assert mech.latest_impressions[0]["fresh"] is True
    assert mech.latest_vision_reviews[0]["findings_by_severity"] == {
        "info": 0,
        "warning": 0,
        "error": 0,
    }

    owner_mismatch = plan.model_copy(deep=True)
    owner_mismatch.workstreams[3].owner = "wire"
    owner_report = run_production_gates(owner_mismatch, workspace, workspace / "liaison")
    owner_gates = {check.id: check.status for check in owner_report.checks}
    assert owner_gates["production.request_owner"] == "fail"

    incomplete_records = plan.model_copy(deep=True)
    incomplete_records.workstreams.append(
        incomplete_records.workstreams[0].model_copy(
            update={
                "id": "sim_record_check",
                "owner": "sim",
                "status": "todo",
                "artifacts": [],
                "request": "sim-done-no-records",
            }
        )
    )
    _request(workspace, "sim-done-no-records", "sim")
    _response(workspace, "sim-done-no-records", "sim", status="done")
    records_report = run_production_gates(incomplete_records, workspace, workspace / "liaison")
    records_gates = {check.id: check.status for check in records_report.checks}
    assert records_gates["production.sister_records"] == "fail"

    accepted_mech = _response(
        workspace,
        "mech-done",
        "mech",
        status="accepted",
        artifacts=[
            {
                "path": "deliverables/mech.txt",
                "sha256": tree_sha256(workspace / "deliverables/mech.txt"),
            }
        ],
        decision_refs=[
            next(entry for entry in status.entries if entry.request == "mech-done").decision_refs[0]
        ],
        impression_refs=[
            next(entry for entry in status.entries if entry.request == "mech-done").impression_refs[
                0
            ]
        ],
    )
    assert accepted_mech.status == "accepted"
    unanswered_report = run_production_gates(plan, workspace, workspace / "liaison")
    unanswered_gates = {check.id: check.status for check in unanswered_report.checks}
    assert unanswered_gates["production.requests_answered"] == "fail"

    final_status = liaison_status(workspace / "liaison", workspace)
    liaison_cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "ux_creator",
            "liaison",
            "--workspace",
            str(workspace),
            "--liaison-dir",
            "liaison",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert liaison_cli.returncode == 0, liaison_cli.stderr + liaison_cli.stdout
    assert json.loads(liaison_cli.stdout)["summary"] == final_status.summary

    plan_path = workspace / "liaison-test.production.json"
    produce_cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "ux_creator",
            "produce",
            str(plan_path),
            "--out",
            str(workspace / "e2e-out"),
            "--workspace",
            str(workspace),
            "--liaison-dir",
            "liaison",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert produce_cli.returncode == 1, produce_cli.stderr + produce_cli.stdout
    produce_payload = json.loads(produce_cli.stdout)
    produce_gates = {check["id"]: check["status"] for check in produce_payload["checks"]}
    assert produce_gates["production.liaison_integrity"] == "fail"
    assert (workspace / "e2e-out" / "liaison-test.production-status.json").is_file()

    mcp_status = asyncio.run(
        mcp_server.dispatch_tool(
            "ux_liaison_status",
            {"workspace": str(workspace), "liaison_dir": "liaison"},
        )
    )
    assert isinstance(mcp_status, dict)
    assert mcp_status["summary"] == final_status.summary
    assert mcp_status["verdict"] == "pass"
