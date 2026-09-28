from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from ux_creator.contract import UXContract
from ux_creator.gates import run_gates
from ux_creator.imports import extract_touchpoints
from ux_creator.projections import write_projections

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT = REPO_ROOT / "examples" / "smart-kettle-product"
CONTRACT = PRODUCT / "smart-kettle.ux.json"


@pytest.fixture()
def product_dict() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _statuses(payload: dict[str, Any], workspace: Path = PRODUCT) -> dict[str, str]:
    report = run_gates(UXContract.model_validate(payload), workspace)
    return {c.id: c.status for c in report.checks}


def test_product_example_passes(product_dict: dict[str, Any]) -> None:
    report = run_gates(UXContract.model_validate(product_dict), PRODUCT)
    assert report.verdict == "pass"
    ids = {c.id for c in report.checks}
    assert {
        "cmf.part_coverage",
        "cmf.primary_color",
        "cmf.marking_contrast",
        "content.feedback_coverage",
        "content.modality_match",
        "content.bard_cue_imported",
    } <= ids


def test_base_example_has_no_cmf_or_content_checks(example_contract: UXContract) -> None:
    ids = {c.id for c in run_gates(example_contract).checks}
    assert not {i for i in ids if i.startswith(("cmf.", "content."))}


def test_unknown_cmf_key_rejected(product_dict: dict[str, Any]) -> None:
    product_dict["cmf"]["mood"] = "calm"
    with pytest.raises(ValueError):
        UXContract.model_validate(product_dict)


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        ("parts", "surface", "nowhere", "unknown surface"),
        ("parts", "color", "teal", "unknown color"),
        ("parts", "material", "steel", "unknown material"),
        ("parts", "finish", "mirror", "unknown finish"),
        ("markings", "surface", "nowhere", "unknown surface"),
        ("markings", "color", "teal", "unknown color"),
    ],
)
def test_cmf_references_must_resolve(
    product_dict: dict[str, Any], section: str, field: str, value: str, message: str
) -> None:
    product_dict["cmf"][section][0][field] = value
    with pytest.raises(ValueError, match=message):
        UXContract.model_validate(product_dict)


def test_cmf_bad_hex_rejected(product_dict: dict[str, Any]) -> None:
    product_dict["cmf"]["palette"][0]["hex"] = "white"
    with pytest.raises(ValueError):
        UXContract.model_validate(product_dict)


def test_cmf_duplicate_ids_rejected(product_dict: dict[str, Any]) -> None:
    product_dict["cmf"]["palette"].append(copy.deepcopy(product_dict["cmf"]["palette"][0]))
    with pytest.raises(ValueError, match="duplicate cmf color"):
        UXContract.model_validate(product_dict)


def test_cmf_part_coverage_fails_for_uncovered_physical_surface(
    product_dict: dict[str, Any],
) -> None:
    product_dict["cmf"]["parts"] = [
        p for p in product_dict["cmf"]["parts"] if p["id"] != "boil_key"
    ]
    product_dict["cmf"]["markings"] = [
        m for m in product_dict["cmf"]["markings"] if m["surface"] != "hardware_button"
    ]
    assert _statuses(product_dict)["cmf.part_coverage"] == "fail"


def test_cmf_primary_color_required(product_dict: dict[str, Any]) -> None:
    for color in product_dict["cmf"]["palette"]:
        if color["role"] == "primary":
            color["role"] = "neutral"
    assert _statuses(product_dict)["cmf.primary_color"] == "fail"


def test_cmf_low_contrast_marking_fails(product_dict: dict[str, Any]) -> None:
    product_dict["cmf"]["palette"].append(
        {"id": "cream", "name": "cream", "hex": "#EFEBE2", "role": "accent"}
    )
    product_dict["cmf"]["markings"][0]["color"] = "cream"
    assert _statuses(product_dict)["cmf.marking_contrast"] == "fail"


def test_cmf_marking_without_part_is_unknown(product_dict: dict[str, Any]) -> None:
    product_dict["cmf"]["markings"][0]["surface"] = "status_led"
    assert _statuses(product_dict)["cmf.marking_contrast"] == "unknown"


def test_content_unknown_feedback_rejected(product_dict: dict[str, Any]) -> None:
    product_dict["content"][0]["feedback"] = "nope"
    with pytest.raises(ValueError, match="unknown feedback"):
        UXContract.model_validate(product_dict)


@pytest.mark.parametrize(
    "source",
    [
        {"kind": "bard_cue", "ref": "cues/x/cues.json", "cue": ""},
        {"kind": "bard_cue", "ref": "", "cue": "done"},
        {"kind": "file", "ref": ""},
        {"kind": "file", "ref": "a.png", "spec": "blink"},
        {"kind": "inline", "spec": ""},
        {"kind": "inline", "spec": "blink", "ref": "a.png"},
    ],
)
def test_content_source_shape_enforced(
    product_dict: dict[str, Any], source: dict[str, str]
) -> None:
    asset = next(a for a in product_dict["content"] if a["id"] == "cue_done")
    asset["source"] = source
    if source["kind"] != "bard_cue":
        asset["modality"] = "audio"
    with pytest.raises(ValueError):
        UXContract.model_validate(product_dict)


def test_bard_cue_must_be_audio(product_dict: dict[str, Any]) -> None:
    asset = next(a for a in product_dict["content"] if a["id"] == "cue_done")
    asset["modality"] = "visual"
    with pytest.raises(ValueError, match="audio only"):
        UXContract.model_validate(product_dict)


def test_uncovered_feedback_fails(product_dict: dict[str, Any]) -> None:
    product_dict["content"] = [
        a for a in product_dict["content"] if a["feedback"] != "app_reminder"
    ]
    assert _statuses(product_dict)["content.feedback_coverage"] == "fail"


def test_modality_mismatch_fails(product_dict: dict[str, Any]) -> None:
    asset = next(a for a in product_dict["content"] if a["id"] == "app_cooling_card")
    asset["modality"] = "haptic"
    statuses = _statuses(product_dict)
    assert statuses["content.modality_match"] == "fail"
    assert statuses["content.feedback_coverage"] == "fail"


def test_bard_cue_not_in_import_fails(product_dict: dict[str, Any]) -> None:
    asset = next(a for a in product_dict["content"] if a["id"] == "cue_done")
    asset["source"]["cue"] = "fanfare"
    assert _statuses(product_dict)["content.bard_cue_imported"] == "fail"


def test_bard_cue_without_import_fails(product_dict: dict[str, Any]) -> None:
    product_dict["imports"] = []
    assert _statuses(product_dict)["content.bard_cue_imported"] == "fail"


def test_bard_cue_manifest_yields_cue_ids() -> None:
    manifest = json.loads(
        (PRODUCT / "cues" / "smart-kettle" / "cues.json").read_text(encoding="utf-8")
    )
    extracted = extract_touchpoints("bard", manifest)
    assert {"cue:boot", "cue:done", "cue:overheat", "cue:press"} <= set(extracted)
    assert "cue-done.mid" in extracted


def test_projections_include_cmf_and_content(product_dict: dict[str, Any], tmp_path: Path) -> None:
    contract = UXContract.model_validate(product_dict)
    paths = write_projections(contract, "smart-kettle", tmp_path)
    sheet = paths["smart-kettle.cmf.md"].read_text(encoding="utf-8")
    assert "`#F4F1EA`" in sheet and "soft matte (matte, MT-11010)" in sheet
    content = json.loads(paths["smart-kettle.content.json"].read_text(encoding="utf-8"))
    assert content["artifact_kind"] == "ux_content_map"
    assert content["authority"] == "none"
    done = next(f for f in content["feedback"] if f["id"] == "beep_done")
    assert done["assets"][0]["source"] == {
        "kind": "bard_cue",
        "ref": "cues/smart-kettle/cues.json",
        "cue": "done",
        "spec": "",
    }
    again = write_projections(contract, "smart-kettle", tmp_path / "again")
    assert (tmp_path / "again" / "smart-kettle.content.json").read_bytes() == paths[
        "smart-kettle.content.json"
    ].read_bytes()
    assert again["smart-kettle.cmf.md"].read_bytes() == paths["smart-kettle.cmf.md"].read_bytes()


def test_base_example_projections_unchanged(example_contract: UXContract, tmp_path: Path) -> None:
    names = set(write_projections(example_contract, "smart-kettle", tmp_path))
    assert "smart-kettle.cmf.md" not in names
    assert "smart-kettle.content.json" not in names
