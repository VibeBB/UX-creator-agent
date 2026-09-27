"""Projection and report tests."""

from __future__ import annotations

import json
from pathlib import Path

from ux_creator.contract import UXContract
from ux_creator.gates import run_gates
from ux_creator.projections import write_projections, write_provenance
from ux_creator.report import write_report


def test_write_projections(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "smart-kettle", tmp_path)
    names = set(paths)
    assert "smart-kettle.morning.journey.mmd" in names
    assert "smart-kettle.power.statechart.mmd" in names
    assert "smart-kettle.power.statechart.puml" in names
    assert "smart-kettle.power.xstate.json" in names
    assert "smart-kettle.power.scxml" in names
    assert "smart-kettle.wireframe.puml" in names
    assert "smart-kettle.stories.json" in names
    assert "smart-kettle.odi.csv" in names
    assert "manifest.json" in names
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["artifacts"]) == len(names) - 1


def test_xstate_shape(example_contract: UXContract, tmp_path: Path) -> None:
    write_projections(example_contract, "x", tmp_path)
    machine = json.loads((tmp_path / "x.power.xstate.json").read_text(encoding="utf-8"))
    assert machine["initial"] == "idle"
    assert machine["states"]["idle"]["on"] == {"press": "heating"}
    assert machine["states"]["done"]["type"] == "final"


def test_scxml_shape(example_contract: UXContract, tmp_path: Path) -> None:
    write_projections(example_contract, "x", tmp_path)
    text = (tmp_path / "x.power.scxml").read_text(encoding="utf-8")
    assert '<scxml xmlns="http://www.w3.org/2005/07/scxml"' in text
    assert '<final id="done"/>' in text
    assert 'event="boiled" target="done"' in text


def test_odi_sorted(example_contract: UXContract, tmp_path: Path) -> None:
    write_projections(example_contract, "x", tmp_path)
    rows = (tmp_path / "x.odi.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0].startswith("job_id")
    assert rows[1].startswith("boil,")  # 14.0 > 11.0


def test_provenance_and_report(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "x", tmp_path)
    write_provenance(example_contract, paths, tmp_path)
    report = run_gates(example_contract, tmp_path)
    write_report(example_contract, report, tmp_path)
    data = json.loads((tmp_path / "ux-report.json").read_text(encoding="utf-8"))
    assert data["verdict"] == "pass"
    assert data["gate"] == "ux-creator"
    assert (tmp_path / "ux-report.md").is_file()
