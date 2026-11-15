"""The authoring smoke test exercises the checked-in SLP v2 example."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "examples/smart-kettle/smart-kettle.ux.json"


def test_e2e_authoring_reconciles_v2_example_files(tmp_path: Path) -> None:
    out_dir = tmp_path / "smart-kettle"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/e2e_authoring.py"),
            "--contract",
            str(CONTRACT),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    report = json.loads((out_dir / "ux-report.json").read_text(encoding="utf-8"))
    liaison = report["lenses"]["liaison"]
    assert liaison["requests"] == 2
    assert liaison["answered"] == 1
    assert liaison["completed"] == 0
    assert liaison["directory"] == "."
    assert liaison["open"] == 1
    assert liaison["by_state"]["answered"] == 1
    assert liaison["by_state"]["open"] == 1
    assert liaison["malformed"] == []
    assert liaison["orphans"] == []
    assert (out_dir / "smart-kettle-led-brightness.ux-request.json").is_file()
    assert (out_dir / "smart-kettle-led-brightness.ux-response.json").is_file()
    triage = json.loads((out_dir / "smart-kettle.triage.json").read_text(encoding="utf-8"))
    assert triage["schema_version"] == 1


def test_e2e_authoring_keeps_source_import_evidence(tmp_path: Path) -> None:
    import hashlib

    source = tmp_path / "source"
    source.mkdir()
    evidence = source / "facts.csv"
    evidence.write_text("label,value\nvolume,2\n", encoding="utf-8")
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    payload["imports"] = [
        {
            "system": "csv",
            "path": evidence.name,
            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        }
    ]
    contract_path = source / CONTRACT.name
    contract_path.write_text(json.dumps(payload), encoding="utf-8")
    out_dir = tmp_path / "report-output"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/e2e_authoring.py"),
            "--contract",
            str(contract_path),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    report = json.loads((out_dir / "ux-report.json").read_text(encoding="utf-8"))
    imported = [check for check in report["checks"] if check["id"].startswith("imports.")]
    assert imported and all(check["status"] == "pass" for check in imported)
