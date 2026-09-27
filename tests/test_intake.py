"""Phase-9 tests: intake touchpoint candidates and reconciliation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ux_creator.advisory import (
    TouchpointCandidate,
    load_intake_records,
    normalize_touchpoint,
    parse_intake_record,
    reconcile_intake,
    write_intake_record,
)
from ux_creator.contract import UXContract
from ux_creator.gates import run_gates
from ux_creator.report import build_report

CONTRACT = "examples/smart-kettle/smart-kettle.ux.json"

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d4944415478da63fcffff3f030005fe02fea72d99"
    "8d0000000049454e44ae426082"
)


def _image(tmp_path: Path, name: str = "kettle_photo") -> Path:
    path = tmp_path / f"{name}.png"
    path.write_bytes(_PNG)
    return path


def test_normalize_touchpoint() -> None:
    assert normalize_touchpoint("Boil Button!") == "boil_button"
    assert normalize_touchpoint("  LED  ") == "led"
    assert normalize_touchpoint("temp-dial") == "temp_dial"
    assert normalize_touchpoint("!!!") == ""


def _payload(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "tool": "ux.intake_touchpoints",
        "stage": "intake",
        "status": "ok",
        "summary": "s",
        "detail": {
            "image_path": "x.png",
            "image_sha256": "sha256:" + "0" * 64,
            "candidates": candidates,
        },
    }


def test_parse_rejects_empty_candidates() -> None:
    assert parse_intake_record(_payload([])) is None


def test_parse_rejects_empty_id() -> None:
    payload = _payload([{"id": "", "evidence": "e"}])
    assert parse_intake_record(payload) is None


def test_parse_rejects_wrong_tool() -> None:
    payload = _payload([{"id": "btn", "evidence": "e"}])
    payload["tool"] = "vision_review"
    assert parse_intake_record(payload) is None


def test_write_load_round_trip(tmp_path: Path) -> None:
    image = _image(tmp_path)
    write_intake_record(
        image,
        [
            TouchpointCandidate(id="button", evidence="chrome dome"),
            TouchpointCandidate(id="Temp Dial", surface="kettle_body", evidence="rotary ring"),
        ],
    )
    records, malformed = load_intake_records(tmp_path)
    assert malformed == []
    assert len(records) == 1
    path, record = records[0]
    assert path.name == "intake-touchpoints-kettle-photo.advisory.json"
    assert record.tool == "ux.intake_touchpoints"
    assert record.stage == "intake"


def test_reconcile_all_branches(example_contract: UXContract, tmp_path: Path) -> None:
    image = _image(tmp_path)
    write_intake_record(
        image,
        [
            TouchpointCandidate(id="button", evidence="chrome dome"),
            TouchpointCandidate(id="lid", evidence="lid hinge"),
            TouchpointCandidate(
                id="temperature_dial",
                surface="thermostat",
                evidence="rotary ring",
            ),
            TouchpointCandidate(id="app_pairing", surface="kettle_body", evidence="qr code"),
        ],
    )
    records, malformed = load_intake_records(tmp_path)
    recon = reconcile_intake(example_contract, records)
    assert recon.declared == ["app_pairing", "button", "lid"]
    assert recon.undeclared == ["temperature_dial"]
    assert "app_notification" in recon.unobserved
    assert "button" not in recon.unobserved
    assert len(recon.surface_mismatch) == 1
    assert recon.surface_mismatch[0].startswith("app_pairing: image says kettle_body")
    assert malformed == []


def test_malformed_listed(tmp_path: Path) -> None:
    bad = tmp_path / "intake-touchpoints-x.advisory.json"
    bad.write_text("{oops", encoding="utf-8")
    records, malformed = load_intake_records(tmp_path)
    assert records == []
    assert malformed == [bad]


def test_report_intake_lens(example_contract: UXContract, tmp_path: Path) -> None:
    report = run_gates(example_contract, tmp_path)
    lens = build_report(example_contract, report, out_dir=tmp_path)
    assert lens["lenses"]["review"]["intake"]["records"] == 0
    write_intake_record(
        _image(tmp_path),
        [TouchpointCandidate(id="temperature_dial", evidence="ring")],
    )
    lens = build_report(example_contract, report, out_dir=tmp_path)
    intake = lens["lenses"]["review"]["intake"]
    assert intake["records"] == 1
    assert intake["undeclared"] == ["temperature_dial"]
    assert intake["declared_count"] == 0


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ux_creator", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_intake_record_and_reconcile(tmp_path: Path) -> None:
    image = _image(tmp_path)
    proc = _run(
        "intake-record",
        str(image),
        "--touchpoint",
        "button@hardware_button=chrome dome",
        "--touchpoint",
        "temperature_dial=rotary ring",
        "--confidence",
        "high",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert json.loads(proc.stdout)["verdict"] == "pass"
    proc = _run("intake-reconcile", "--contract", CONTRACT, "--out-dir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["verdict"] == "pass"
    assert payload["declared"] == ["button"]
    assert payload["undeclared"] == ["temperature_dial"]


def test_cli_intake_record_bad_spec(tmp_path: Path) -> None:
    proc = _run("intake-record", str(_image(tmp_path)), "--touchpoint", "noequals")
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["verdict"] == "fail"
