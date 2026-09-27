"""Phase-6 tests: sister ux-response reconciliation + liaison lens."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ux_creator.contract import UXContract
from ux_creator.gates import run_gates
from ux_creator.report import build_report
from ux_creator.responses import liaison_status, load_responses

CONTRACT = "examples/smart-kettle/smart-kettle.ux.json"
EXAMPLE_RESPONSE = "examples/smart-kettle/smart-kettle-led_brightness.ux-response.json"


def _request(dir: Path, stem: str, target: str, risk: str = "high") -> Path:
    path = dir / f"{stem}.ux-request.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "system": "ux-creator",
                "target_agent": target,
                "risk": risk,
                "rationale": "r",
                "requested_changes": ["c"],
            }
        ),
        encoding="utf-8",
    )
    return path


def _response(
    dir: Path,
    stem: str,
    responder: str,
    status: str = "accepted",
    request: str | None = None,
    name: str | None = None,
) -> Path:
    path = dir / (name or f"{stem}.ux-response.json")
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "system": "ux-creator",
                "request": request or stem,
                "responder": responder,
                "status": status,
                "reason": "r",
                "artifacts": [],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_answered_open_mismatched(tmp_path: Path) -> None:
    _request(tmp_path, "r1", "circuit")
    _response(tmp_path, "r1", "circuit")
    _request(tmp_path, "r2", "mech")
    _request(tmp_path, "r3", "mech")
    _response(tmp_path, "r3", "wire")  # wrong responder
    status = liaison_status(tmp_path, tmp_path)
    states = {e.request: e.state for e in status.entries}
    assert states == {"r1": "answered", "r2": "open", "r3": "mismatched"}
    r1 = next(e for e in status.entries if e.request == "r1")
    assert r1.response_status == "accepted"
    assert status.orphans == []


def test_orphan_and_normalisation(tmp_path: Path) -> None:
    _request(tmp_path, "r1", "circuit")
    _response(tmp_path, "orphan", "circuit", request="orphan.ux-request.json")
    status = liaison_status(tmp_path, tmp_path)
    assert len(status.orphans) == 1
    assert "orphan" in status.orphans[0]


def test_malformed_listed_not_raised(tmp_path: Path) -> None:
    (tmp_path / "broken.ux-response.json").write_text("{oops", encoding="utf-8")
    _request(tmp_path, "r1", "circuit")
    _response(tmp_path, "r1", "circuit")
    records, malformed = load_responses(tmp_path)
    assert len(records) == 1
    assert malformed == [tmp_path / "broken.ux-response.json"]
    status = liaison_status(tmp_path, tmp_path)
    assert status.malformed == [str(tmp_path / "broken.ux-response.json")]


def test_malformed_request_listed(tmp_path: Path) -> None:
    (tmp_path / "bad.ux-request.json").write_text("[]", encoding="utf-8")
    status = liaison_status(tmp_path, tmp_path)
    assert status.malformed == [str(tmp_path / "bad.ux-request.json")]


def test_latest_response_wins(tmp_path: Path) -> None:
    _request(tmp_path, "r1", "circuit")
    _response(tmp_path, "r1", "circuit", status="rejected", name="a-r1.ux-response.json")
    _response(tmp_path, "r1", "circuit", status="accepted", name="z-r1.ux-response.json")
    status = liaison_status(tmp_path, tmp_path)
    entry = status.entries[0]
    assert entry.state == "answered"
    assert entry.response_status == "accepted"
    assert entry.response_path.endswith("z-r1.ux-response.json")


def test_unknown_responder_is_malformed(tmp_path: Path) -> None:
    _response(tmp_path, "r1", "ghost-agent")
    records, malformed = load_responses(tmp_path)
    assert records == []
    assert len(malformed) == 1


def test_liaison_lens_numbers(tmp_path: Path, contract_dict: dict[str, Any]) -> None:
    contract = UXContract.model_validate(contract_dict)
    report = run_gates(contract, tmp_path)
    _request(tmp_path, "r-acc", "circuit", risk="high")
    _response(tmp_path, "r-acc", "circuit", status="accepted")
    _request(tmp_path, "r-rej", "mech", risk="high")
    _response(tmp_path, "r-rej", "mech", status="rejected")
    _request(tmp_path, "r-open", "wire", risk="low")
    _response(tmp_path, "r-mis", "mech", request="r-mis")
    _request(tmp_path, "r-mis", "wire", risk="low")
    lens = build_report(contract, report, out_dir=tmp_path)["lenses"]["liaison"]
    assert lens["requests"] == 4
    assert lens["answered"] == 2
    assert lens["open"] == 1
    assert lens["mismatched"] == 1
    assert lens["by_status"]["accepted"] == 2
    assert lens["by_status"]["rejected"] == 1
    assert lens["rejected_high_risk"] == ["r-rej"]


def test_verdict_unchanged_with_responses(contract_dict: dict[str, Any], tmp_path: Path) -> None:
    contract = UXContract.model_validate(contract_dict)
    report = run_gates(contract, tmp_path)
    base = build_report(contract, report, out_dir=tmp_path)
    _request(tmp_path, "r-rej", "mech", risk="high")
    _response(tmp_path, "r-rej", "mech", status="rejected")
    with_responses = build_report(contract, report, out_dir=tmp_path)
    assert base["verdict"] == with_responses["verdict"]


def test_example_response_file() -> None:
    payload = json.loads(Path(EXAMPLE_RESPONSE).read_text(encoding="utf-8"))
    assert payload["responder"] == "circuit"
    assert payload["status"] == "accepted"
    assert payload["request"] == "smart-kettle-led_brightness"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ux_creator", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_liaison_round_trip(tmp_path: Path) -> None:
    _request(tmp_path, "r1", "circuit")
    _response(tmp_path, "r1", "circuit", status="deferred")
    proc = _run("liaison", "--out-dir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["verdict"] == "pass"
    assert payload["stage"] == "liaison"
    assert payload["entries"][0]["state"] == "answered"
    assert payload["entries"][0]["response_status"] == "deferred"
