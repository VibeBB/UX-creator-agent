"""Check bounded collection against real VRP writers and returned-image hooks."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from ux_creator import _vrp, mcp_server
from ux_creator.cli import main
from ux_creator.records import record_reconcile, record_vision_review
from ux_creator.render import ImageIdentity, RenderResult
from ux_creator.review_checkpoint import review_checkpoint

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "plugins/ux/hooks/scripts/record_image_observation.py"


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("OPENHANDS_SESSION_ID", raising=False)
    monkeypatch.delenv("UX_IMAGE_OBSERVATIONS", raising=False)
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    (tmp_path / "contract.json").write_text('{"states": ["Idle", "Ready"]}', encoding="utf-8")
    (tmp_path / "diagram.png").write_bytes(b"Idle Ready: synthetic image fixture")
    return tmp_path


def _call(root: Path, action: str, **fields: Any) -> dict[str, Any]:
    return review_checkpoint(
        {"action": action, "checkpoint_id": "test", "session_id": "coordinator", **fields}, root
    )


def _create(root: Path) -> dict[str, Any]:
    return _call(
        root,
        "create",
        contract_path="contract.json",
        sources=[{"image_path": "diagram.png", "checklist": "statechart"}],
    )


def _active(result: dict[str, Any]) -> dict[str, Any]:
    return next(pair for pair in result["pairs"] if pair["active"])


def _write_review(root: Path, role: str, primary: str | None = None, **fields: Any) -> str:
    """Synthetic fixtures exercise evidence contracts, never visual perception."""
    session = fields.pop("session_id", role + "-native-child")
    image = root / (fields.get("image_path") or "diagram.png")
    observed = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(
            {
                "session_id": session,
                "working_dir": str(root),
                "tool_name": "file_editor",
                "tool_input": {"command": "view", "path": str(image)},
                "tool_response": {
                    "content": [
                        {
                            "type": "image",
                            "image_urls": [
                                "data:image/png;base64,"
                                + base64.b64encode(image.read_bytes()).decode("ascii")
                            ],
                        }
                    ]
                },
            }
        ),
        capture_output=True,
        text=True,
        check=False,
        env=dict(os.environ),
    )
    assert observed.returncode == 0, observed.stderr
    words = {
        "primary": "Source transitions label Idle Ready",
        "blind": "Independent Idle layout spacing",
        "tiebreak": "Additional Idle alignment comparison",
    }[role]
    summary = (
        ". ".join(
            f"{words} observation {i} explains the concrete arrangement of this synthetic fixture "
            f"with a distinct {role} interpretation of its labels and accessible progression"
            for i in range(4)
        )
        + "."
    )
    payload: dict[str, Any] = {
        "session_id": session,
        "image_path": "diagram.png",
        "model": "fixture-only",
        "checklist": "statechart",
        "reviewer": role,
        "impression": summary,
        "delta": f"The {role} fixture exercises a separate reviewer identity and role binding.",
        "findings": [],
        "unknowns": [],
        "confidence": "low",
        "facets": {
            "observed": ["Idle has a visible label", "Ready has a visible label"],
            "works": ["The transition labels remain distinct"],
            "concerns": [],
            "no_concerns_reason": "This fixture only exercises evidence binding, not quality.",
            "feelings": {"maker": "Can identify both state names", "user": "Can follow the labels"},
            "next_actions": ["Perform a real visual review separately"],
        },
        "claims": [{"text": "The fixture names Idle", "anchor": "Idle", "artifact": "diagram.png"}],
        "lookback": [{"claim": 0, "verdict": "confirmed", "note": "Synthetic fixture token"}],
    }
    if primary:
        payload["primary_event_id"] = primary
    else:
        payload["coordinator_session_id"] = "coordinator"
    payload.update(fields)
    return str(record_vision_review(payload, root)["record"]["event_id"])


def _collect(root: Path, started: dict[str, Any], event: str) -> dict[str, Any]:
    return _call(root, "collect", pair_id=_active(started)["id"], review_event_id=event)


@pytest.mark.parametrize("replacement_tile", ["tile.png", "replacement.png"])
def test_current_review_keeps_prior_original_debt_after_auxiliary_replacement(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, replacement_tile: str
) -> None:
    """Use real MCP receipts, VRP writers and native Stop without an LLM call."""
    image = workspace / "diagram.png"

    def render(_directory: Path, **_kwargs: object) -> list[RenderResult]:
        return [
            RenderResult(
                image,
                image,
                "ok",
                "synthetic fixture",
                ImageIdentity(
                    path=str(image),
                    sha256=_vrp.sha256_file(image),
                    owner_plugin="ux",
                    origin="renderer",
                ),
            )
        ]

    monkeypatch.setattr(mcp_server, "render_all", render)

    def deliver(tile_name: str) -> None:
        (workspace / tile_name).write_bytes(b"synthetic tile")
        result = asyncio.run(
            mcp_server.call_tool(
                None,
                mcp_server.types.CallToolRequestParams(
                    name="ux_render",
                    arguments={
                        "dir": ".",
                        "image_details": [
                            {"path": tile_name, "parents": ["diagram.png"], "operation": "tile"}
                        ],
                    },
                ),
            )
        )
        assert not result.is_error
        observed = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(
                {
                    "session_id": "coordinator",
                    "working_dir": str(workspace),
                    "tool_name": "ux_render",
                    "tool_response": result.model_dump(by_alias=True),
                }
            ),
            capture_output=True,
            text=True,
            check=False,
        )
        assert observed.returncode == 0 and not observed.stderr

    def hook(action: str) -> int:
        return subprocess.run(
            [sys.executable, str(HOOK.with_name("require_records.py")), action],
            input=json.dumps({"session_id": "coordinator", "working_dir": str(workspace)}),
            capture_output=True,
            text=True,
            check=False,
        ).returncode

    assert hook("record-context") == 0
    deliver("tile.png")
    original_sha = _vrp.sha256_file(image)
    image.write_bytes(b"Idle Ready: updated formal revision")
    deliver(replacement_tile)
    assert hook("stop") == 2
    status_path = workspace / "observations/ux/.sessions/coordinator.status.json"
    before = json.loads(status_path.read_text(encoding="utf-8"))
    assert any("viewed image" in problem for problem in before["problems"])
    assert not any("ancestry unknown" in problem for problem in before["problems"])
    _write_review(workspace, "primary")
    assert hook("stop") == 2
    after = json.loads(status_path.read_text(encoding="utf-8"))
    assert len(after["problems"]) == 1 and original_sha[:12] in after["problems"][0]
    assert "ancestry unknown" not in after["problems"][0]
    assert after["stop_denials"] == 2
    # Auxiliary debt retires, but the unreviewed historical original still fails.
    assert after["record_compliance"] == "fail"
    assert after["acceptance"] == after["run_completion"] == "unknown"


def test_event_only_review_preserves_history_without_blocking_image_collection(
    workspace: Path,
) -> None:
    event = _write_review(
        workspace, "primary", image_path=None, source_event_id="a" * 64, coordinator_session_id=None
    )
    assert _create(workspace)["status"] == "paused"
    assert _call(workspace, "status")["status"] == "paused"
    started = _call(workspace, "start")
    assert _active(started)["after_sequence"] == 1
    with pytest.raises(ValueError, match="review evidence unknown"):
        _collect(workspace, started, event)
    assert _call(workspace, "status")["status"] == "running"


def _start_role(root: Path, role: str) -> tuple[dict[str, Any], str | None]:
    _create(root)
    started = _call(root, "start")
    if role == "primary":
        return started, None
    primary = _write_review(root, "primary")
    _collect(root, started, primary)
    started = _call(root, "start")
    if role == "blind":
        return started, primary
    blind = _write_review(
        root,
        "blind",
        primary,
        findings=[{"category": "spacing", "severity": "error", "note": "Idle label overlap"}],
    )
    _collect(root, started, blind)
    assert (
        record_reconcile({"session_id": "coordinator", "reviews": [primary, blind]}, root)[
            "record"
        ]["outcome"]
        == "disagree"
    )
    _call(root, "tiebreak", pair_id=_active(started)["id"])
    return _call(root, "start"), primary


@pytest.mark.parametrize("role", ["primary", "blind", "tiebreak"])
@pytest.mark.parametrize("attempt", [1, 2])
def test_start_recovers_written_evidence_after_interruption_without_spending_an_attempt(
    workspace: Path, role: str, attempt: int
) -> None:
    started, primary = _start_role(workspace, role)
    if attempt == 2:
        _call(workspace, "pause", reason="first attempt timed out before writing")
        started = _call(workspace, "start")
    event = _write_review(workspace, role, primary)
    _call(workspace, "pause", reason="record written, final native reply interrupted")
    recovered = _call(workspace, "start")
    pair = next(p for p in recovered["pairs"] if p["id"] == _active(started)["id"])
    assert pair["review_event_id"] == event and pair["attempts"] == attempt
    assert pair["after_sequence"] == _active(started)["after_sequence"]
    assert not pair["active"] and pair["gap"] is None
    assert len(pair["attempt_gaps"]) == attempt
    assert recovered["acceptance"] == "unknown"
    if role == "primary":
        assert _active(recovered)["role"] == "blind"
    else:
        assert recovered["status"] == "collected" and recovered["delegate"] is None
    assert _call(workspace, "status")["pairs"] == recovered["pairs"]


def test_retry_recovery_rejects_evidence_from_before_the_first_reservation(workspace: Path) -> None:
    event = _write_review(workspace, "primary")
    _create(workspace)
    _call(workspace, "start")
    _call(workspace, "pause", reason="interrupted without writing a fresh record")
    retry = _call(workspace, "start")
    assert _active(retry)["attempts"] == 2
    with pytest.raises(ValueError, match="review evidence unknown"):
        _collect(workspace, retry, event)


def test_retry_recovery_rejects_ambiguous_matching_records(workspace: Path) -> None:
    _start_role(workspace, "primary")
    _write_review(workspace, "primary", session_id="first-child")
    _write_review(
        workspace,
        "primary",
        session_id="second-child",
        impression=(
            "Idle names the token used to ground this second synthetic inspection in its source. "
            "A separate narrative distinguishes two structurally valid primary records "
            "so recovery must refuse to choose between them without additional information. "
            "Neither entry establishes perceptual quality because the underlying bytes are only "
            "a test fixture for event identity and coordinator relationships. "
            "The expected outcome is an ambiguity error with no attempt consumed or state edited."
        ),
    )
    _call(workspace, "pause", reason="multiple returned records need investigation")
    checkpoint = workspace / "observations/ux/review-checkpoints/test.json"
    before = checkpoint.read_bytes()
    with pytest.raises(ValueError, match="ambiguous uncollected review evidence"):
        _call(workspace, "start")
    assert checkpoint.read_bytes() == before


def test_retry_recovery_cannot_promote_a_record_without_delivery_evidence(workspace: Path) -> None:
    _start_role(workspace, "primary")
    _write_review(workspace, "primary")
    _call(workspace, "pause", reason="reply interrupted after writing")
    (workspace / "observations/ux/image-observations.jsonl").unlink()
    retry = _call(workspace, "start")
    assert _active(retry)["attempts"] == 2
    assert not any(p["review_event_id"] for p in retry["pairs"])
    assert retry["acceptance"] == "unknown"


@pytest.mark.parametrize("same_bytes", [False, True])
def test_unrelated_symlinked_review_image_does_not_block_retry(
    workspace: Path, same_bytes: bool
) -> None:
    _start_role(workspace, "primary")
    _call(workspace, "pause", reason="provider unavailable before a record was written")
    other = workspace / "other.png"
    other.write_bytes(
        (workspace / "diagram.png").read_bytes()
        if same_bytes
        else b"Idle Ready: another synthetic image"
    )
    _write_review(
        workspace,
        "primary",
        image_path="other.png",
        session_id="unrelated-child",
        claims=[{"text": "Other fixture names Idle", "anchor": "Idle", "artifact": "other.png"}],
    )
    rows, problems = _vrp.verify_log(
        workspace / "observations/ux/vision-reviews.jsonl", "vision_review"
    )
    assert not problems and rows[0]["image_delivery"]["status"] == "bound"
    other.unlink()
    other.symlink_to(workspace / "diagram.png")
    retry = _call(workspace, "start")
    assert _active(retry)["attempts"] == 2
    assert retry["delegate"] is not None and retry["acceptance"] == "unknown"


def test_restart_reuses_collected_sha_role_and_blind_brief_is_opaque(workspace: Path) -> None:
    assert _create(workspace)["acceptance"] == "unknown"
    started = _call(workspace, "start")
    assert "resume" not in started["delegate"]
    primary = _write_review(workspace, "primary")
    _collect(workspace, started, primary)
    # Reload from disk rather than carrying a live coordinator object.
    checkpoint = workspace / "observations/ux/review-checkpoints/test.json"
    before = (checkpoint.read_bytes(), checkpoint.stat().st_mtime_ns)
    first = _call(workspace, "status")
    assert first == _call(workspace, "status")
    assert before == (checkpoint.read_bytes(), checkpoint.stat().st_mtime_ns)
    blind = _call(workspace, "start")
    assert _active(blind)["role"] == "blind"
    brief = blind["delegate"]["prompt"]
    assert primary in brief and "reviewer=blind" in brief
    assert "observation 0" not in brief and "checkpoint" not in brief
    event = _write_review(workspace, "blind", primary)
    final = _collect(workspace, blind, event)
    assert final["status"] == "collected" and final["acceptance"] == "unknown"
    assert not final["gaps"]
    assert [p["attempts"] for p in final["pairs"]] == [1, 1]
    with pytest.raises(ValueError, match="no eligible"):
        _call(workspace, "start")


def test_interruption_serializes_children_and_caps_fresh_attempts(workspace: Path) -> None:
    _create(workspace)
    for reason in ("provider 429 retry exhausted", "native budget exhausted"):
        _call(workspace, "start")
        with pytest.raises(ValueError, match="active child"):
            _call(workspace, "start")
        _call(workspace, "pause", reason=reason)
    status = _call(workspace, "status")
    assert status["status"] == "blocked"
    assert status["pairs"][0]["attempts"] == 2
    assert any("native budget exhausted" in gap for gap in status["gaps"])
    with pytest.raises(ValueError, match="no eligible"):
        _call(workspace, "start")
    with pytest.raises(ValueError, match="already exists"):
        _create(workspace)


@pytest.mark.parametrize("source", ["contract.json", "diagram.png"])
@pytest.mark.parametrize("damage", ["rewrite", "delete", "symlink"])
def test_changed_or_unavailable_inputs_block_resume(
    workspace: Path, source: str, damage: str
) -> None:
    _create(workspace)
    path = workspace / source
    if damage == "rewrite":
        path.write_bytes(b"changed revision")
    else:
        path.unlink()
        if damage == "symlink":
            path.symlink_to(workspace / "other")
    assert _call(workspace, "status")["status"] == "blocked"
    with pytest.raises(ValueError, match="checkpoint blocked"):
        _call(workspace, "start")


@pytest.mark.parametrize("damage", ["missing", "malformed", "edited", "delivery"])
def test_damaged_collected_evidence_never_becomes_a_cached_success(
    workspace: Path, damage: str
) -> None:
    _create(workspace)
    started = _call(workspace, "start")
    event = _write_review(workspace, "primary")
    _collect(workspace, started, event)
    log = workspace / "observations/ux/vision-reviews.jsonl"
    if damage == "missing":
        log.unlink()
    elif damage == "malformed":
        log.write_text("{bad\n", encoding="utf-8")
    elif damage == "delivery":
        (log.parent / "image-observations.jsonl").unlink()
    else:
        log.write_text(
            log.read_text(encoding="utf-8").replace("fixture-only", "edited"), encoding="utf-8"
        )
    if damage in {"edited", "malformed"}:
        with pytest.raises(ValueError, match="evidence unknown"):
            _call(workspace, "status")
    else:
        assert _call(workspace, "status")["status"] == "blocked"


@pytest.mark.parametrize("mismatch", ["session", "checklist", "old", "delivery", "role"])
def test_collection_rejects_unbound_evidence(workspace: Path, mismatch: str) -> None:
    _create(workspace)
    event = ""
    fields = {"coordinator_session_id": "another"} if mismatch == "session" else {}
    if mismatch == "checklist":
        fields["checklist"] = "wireframe"
    if mismatch == "old":
        event = _write_review(workspace, "primary")
    started = _call(workspace, "start")
    if mismatch != "old":
        event = _write_review(workspace, "primary", **fields)
    if mismatch == "delivery":
        (workspace / "observations/ux/image-observations.jsonl").unlink()
    if mismatch == "role":
        path = workspace / "observations/ux/vision-reviews.jsonl"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["reviewer"] = "blind"
        record.pop("coordinator_session_id")
        record["event_id"] = event = _vrp.compute_event_id(record)
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="review evidence unknown"):
        _collect(workspace, started, event)
    assert _call(workspace, "status")["status"] == "running"


@pytest.mark.parametrize("damage", ["missing", "round", "metrics", "source"])
def test_tiebreak_requires_actual_disagreement_and_is_added_once(
    workspace: Path, damage: str
) -> None:
    _create(workspace)
    primary_start = _call(workspace, "start")
    primary = _write_review(workspace, "primary")
    _collect(workspace, primary_start, primary)
    blind_start = _call(workspace, "start")
    blind = _write_review(
        workspace,
        "blind",
        primary,
        findings=[{"category": "spacing", "severity": "error", "note": "Idle label overlap"}],
        facets={
            "observed": ["Idle has a visible label", "Ready has a visible label"],
            "works": ["The state names remain distinguishable"],
            "concerns": [
                {
                    "id": "spacing",
                    "text": "Idle has insufficient spacing",
                    "severity": "error",
                    "about": "self",
                    "anchor": "Idle",
                }
            ],
            "feelings": {"maker": "Would increase label spacing", "user": "May confuse the labels"},
            "next_actions": ["Measure spacing before changing the contract"],
        },
    )
    _collect(workspace, blind_start, blind)
    pair = _active(primary_start)["id"]
    with pytest.raises(ValueError, match="disagreement"):
        _call(workspace, "tiebreak", pair_id=pair)
    reconcile = record_reconcile(
        {"session_id": "coordinator", "reviews": [primary, blind]}, workspace
    )
    assert reconcile["record"]["outcome"] == "disagree"
    _call(workspace, "tiebreak", pair_id=pair)
    with pytest.raises(ValueError, match="only once"):
        _call(workspace, "tiebreak", pair_id=pair)
    started = _call(workspace, "start")
    assert _active(started)["role"] == "tiebreak"
    event = _write_review(
        workspace,
        "tiebreak",
        primary,
        findings=[{"category": "contrast", "severity": "warning", "note": "Idle contrast differs"}],
    )
    assert _collect(workspace, started, event)["status"] == "collected"
    second = record_reconcile(
        {"session_id": "coordinator", "reviews": [primary, blind, event]}, workspace
    )
    assert second["record"]["outcome"] == "unresolved"
    assert _call(workspace, "status")["acceptance"] == "unknown"
    log = workspace / "observations/ux/reconciles.jsonl"
    if damage == "missing":
        log.unlink()
    else:
        # Even rehashed, structurally valid round-1 edits cannot authorize reuse.
        row = dict(reconcile["record"])
        if damage == "round":
            row["round"] = 2
        elif damage == "metrics":
            row["metrics"] = {}
        else:
            row["image_sha256"] = "b" * 64
        row["event_id"] = _vrp.compute_event_id(row)
        log.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert _call(workspace, "status")["status"] == "blocked"
    with pytest.raises(ValueError, match="checkpoint blocked"):
        _call(workspace, "start")


def test_checkpoint_owner_checksum_and_path_are_enforced(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = _create(workspace)
    with pytest.raises(ValueError, match="different coordinator"):
        _call(workspace, "status", session_id="other")
    monkeypatch.setenv("OPENHANDS_SESSION_ID", "native-other")
    with pytest.raises(ValueError, match="OPENHANDS_SESSION_ID"):
        _call(workspace, "status")
    monkeypatch.delenv("OPENHANDS_SESSION_ID")
    with pytest.raises(ValueError):
        _call(
            workspace,
            "create",
            checkpoint_id="../escape",
            contract_path="contract.json",
            sources=[],
        )
    path = workspace / created["checkpoint"]
    path.write_text(
        path.read_text(encoding="utf-8").replace('"attempts": 0', '"attempts": 1'), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="integrity unknown"):
        _call(workspace, "status")


def test_cli_mcp_and_non_idempotent_annotation(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request = {
        "action": "create",
        "checkpoint_id": "test",
        "session_id": "coordinator",
        "contract_path": "contract.json",
        "sources": [{"image_path": "diagram.png", "checklist": "statechart"}],
    }
    (workspace / "request.json").write_text(json.dumps(request), encoding="utf-8")
    assert main(["review-checkpoint", "--json", "request.json"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "paused"
    result = asyncio.run(
        mcp_server.dispatch_tool(
            "ux_review_checkpoint",
            {"action": "start", "checkpoint_id": "test", "session_id": "coordinator"},
        )
    )
    assert isinstance(result, dict) and result["status"] == "running"
    tool = next(t for t in mcp_server.tool_specs() if t.name == "ux_review_checkpoint")
    assert (
        tool.annotations
        and not tool.annotations.read_only_hint
        and not tool.annotations.idempotent_hint
    )
