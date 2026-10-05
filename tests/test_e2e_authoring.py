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
    assert liaison["open"] == 1
    assert liaison["by_state"]["answered"] == 1
    assert liaison["by_state"]["open"] == 1
    assert liaison["malformed"] == []
    assert liaison["orphans"] == []
    assert (out_dir / "smart-kettle-led-brightness.ux-request.json").is_file()
    assert (out_dir / "smart-kettle-led-brightness.ux-response.json").is_file()
    triage = json.loads(
        (out_dir / "smart-kettle.triage.json").read_text(encoding="utf-8")
    )
    assert triage["schema_version"] == 1
