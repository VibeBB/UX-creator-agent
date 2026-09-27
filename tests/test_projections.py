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


def test_blueprint_puml_written(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "x", tmp_path)
    text = paths["x.blueprint.puml"].read_text(encoding="utf-8")
    assert text.startswith("@startuml")
    assert "|Customer|" in text and "|Frontstage|" in text and "|Backstage|" in text
    assert "|Support|" in text and text.rstrip().endswith("@enduml")
    assert ":morning/boil — touchpoints" in text


def test_blueprint_puml_absent_without_service_blueprint(
    example_contract: UXContract, tmp_path: Path
) -> None:
    contract = UXContract.model_validate(
        {**example_contract.model_dump(by_alias=True), "service_blueprint": None}
    )
    paths = write_projections(contract, "x", tmp_path)
    assert not any(fn.endswith(".blueprint.puml") for fn in paths)


def test_blueprint_escapes_semicolons(example_contract: UXContract, tmp_path: Path) -> None:
    contract = UXContract.model_validate(
        {
            **example_contract.model_dump(by_alias=True),
            "service_blueprint": {
                "frontstage": ["press; brew\nnow"],
                "backstage": [],
                "support_processes": [],
            },
        }
    )
    paths = write_projections(contract, "x", tmp_path)
    text = paths["x.blueprint.puml"].read_text(encoding="utf-8")
    assert ":press, brew now;" in text
    assert "; brew" not in text


def test_emotion_mmd_and_json(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "x", tmp_path)
    mmd = paths["x.morning.emotion.mmd"].read_text(encoding="utf-8")
    assert mmd.startswith("xychart-beta")
    assert 'x-axis ["pair_app", "fill", "boil", "pour", "forgot"]' in mmd
    data = json.loads(paths["x.morning.emotion.json"].read_text(encoding="utf-8"))
    assert [r["stage"] for r in data] == ["pair_app", "fill", "boil", "pour", "forgot"]
    assert all(set(r) == {"stage", "emotion", "pain_points", "jobs"} for r in data)


def test_manifest_contains_new_files(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "x", tmp_path)
    manifest = json.loads(paths["manifest.json"].read_text(encoding="utf-8"))
    names = {a["path"] for a in manifest["artifacts"]}
    assert "x.blueprint.puml" in names
    assert "x.morning.emotion.mmd" in names
    assert "x.morning.emotion.json" in names


def test_mindmap_mmd(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "x", tmp_path)
    text = paths["x.mindmap.mmd"].read_text(encoding="utf-8")
    assert text.startswith("mindmap")
    assert "root((smart-kettle))" in text
    assert "    Personas" in text and "    Jobs" in text
    assert "    Surfaces" in text and "    Journeys" in text
    assert "      boil -appropriate-" in text


def test_sequence_puml(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "x", tmp_path)
    text = paths["x.morning.sequence.puml"].read_text(encoding="utf-8")
    assert text.startswith("@startuml")
    assert 'actor "user" as U' in text or "actor" in text
    assert "== boil (use) ==" in text
    assert "U -> S_" in text
    assert "note right of U : emotion 4/5" in text
    assert text.rstrip().endswith("@enduml")


def test_wbs_puml(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "x", tmp_path)
    text = paths["x.wbs.puml"].read_text(encoding="utf-8")
    assert text.startswith("@startwbs")
    assert "* smart-kettle" in text
    assert "** hardware_button (hardware)" in text
    assert "*** control: boil_button" in text
    assert "** Implementation spec" in text
    assert text.rstrip().endswith("@endwbs")


def test_manifest_phase11_files(example_contract: UXContract, tmp_path: Path) -> None:
    paths = write_projections(example_contract, "x", tmp_path)
    manifest = json.loads(paths["manifest.json"].read_text(encoding="utf-8"))
    names = {a["path"] for a in manifest["artifacts"]}
    assert "x.mindmap.mmd" in names
    assert "x.morning.sequence.puml" in names
    assert "x.wbs.puml" in names
