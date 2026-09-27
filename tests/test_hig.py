"""Phase-11 tests: HIG numeric gates (target size, WCAG contrast)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ux_creator.contract import UXContract
from ux_creator.gates import contrast_ratio, run_gates


def _contract(contract_dict: dict[str, Any], controls: list[dict[str, Any]]) -> UXContract:
    return UXContract.model_validate({**contract_dict, "controls": controls})


def _hig(contract: UXContract) -> dict[str, Any]:
    report = run_gates(contract, Path.cwd())
    return {c.id: c for c in report.checks if c.id.startswith("hig.")}


def test_contrast_math() -> None:
    assert round(contrast_ratio("#000000", "#FFFFFF"), 2) == 21.0
    assert round(contrast_ratio("#777777", "#FFFFFF"), 2) == 4.48
    assert round(contrast_ratio("#FFFFFF", "#0057D9"), 2) > 4.5


def test_target_size_pass(contract_dict: dict[str, Any]) -> None:
    contract = _contract(
        contract_dict,
        [
            {
                "id": "b1",
                "surface": "btn",
                "kind": "button",
                "width_mm": 14,
                "height_mm": 8,
            }
        ],
    )
    check = _hig(contract)["hig.target_size"]
    assert check.status == "pass"
    assert check.measured == 8


def test_target_size_fail(contract_dict: dict[str, Any]) -> None:
    contract = _contract(
        contract_dict,
        [
            {
                "id": "tiny",
                "surface": "btn",
                "kind": "touch",
                "width_mm": 5,
                "height_mm": 10,
            }
        ],
    )
    check = _hig(contract)["hig.target_size"]
    assert check.status == "fail"
    assert "tiny:5.0x10.0" in check.detail
    assert check.measured == 5.0


def test_target_size_ignores_unsized_and_links(contract_dict: dict[str, Any]) -> None:
    contract = _contract(
        contract_dict,
        [
            {"id": "u1", "surface": "btn", "kind": "button"},
            {
                "id": "l1",
                "surface": "btn",
                "kind": "link",
                "width_mm": 2,
                "height_mm": 2,
            },
        ],
    )
    check = _hig(contract)["hig.target_size"]
    assert check.status == "pass"
    assert check.detail == "no sized controls"


def test_contrast_fail_and_large_text(contract_dict: dict[str, Any]) -> None:
    contract = _contract(
        contract_dict,
        [
            {
                "id": "grey",
                "surface": "btn",
                "kind": "touch",
                "fg": "#777777",
                "bg": "#FFFFFF",
            },
            {
                "id": "big",
                "surface": "btn",
                "kind": "touch",
                "fg": "#777777",
                "bg": "#FFFFFF",
                "large_text": True,
            },
        ],
    )
    check = _hig(contract)["hig.contrast"]
    assert check.status == "fail"
    assert "grey:4.48" in check.detail
    assert "big" not in check.detail
    assert check.measured == 4.48


def test_contrast_no_colored(contract_dict: dict[str, Any]) -> None:
    contract = _contract(contract_dict, [{"id": "b", "surface": "btn", "kind": "button"}])
    assert _hig(contract)["hig.contrast"].detail == "no colored controls"


def test_validator_unknown_surface(contract_dict: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="unknown surface"):
        _contract(contract_dict, [{"id": "b", "surface": "ghost", "kind": "button"}])


def test_validator_unknown_touchpoint(contract_dict: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="unknown touchpoint"):
        _contract(
            contract_dict,
            [{"id": "b", "surface": "btn", "kind": "button", "touchpoint": "ghost"}],
        )


def test_validator_partial_colors(contract_dict: dict[str, Any]) -> None:
    for bad in (
        {"fg": "#FFFFFF"},
        {"bg": "#FFFFFF"},
        {"fg": "white", "bg": "#000000"},
    ):
        with pytest.raises(ValidationError):
            _contract(
                contract_dict,
                [{"id": "b", "surface": "btn", "kind": "button", **bad}],
            )


def test_example_contract_controls_pass(
    example_contract: UXContract,
) -> None:
    hig = _hig(example_contract)
    assert hig["hig.target_size"].status == "pass"
    assert hig["hig.contrast"].status == "pass"
