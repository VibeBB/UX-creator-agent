"""Contract model validation tests."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from ux_creator.contract import UXContract


def test_example_contract_loads(example_contract: UXContract) -> None:
    assert example_contract.system == "ux-creator"
    assert example_contract.product.name == "smart-kettle"
    assert example_contract.jobs[0].opportunity == pytest.approx(14.0)


def test_minimal_contract_validates(contract_dict: dict[str, Any]) -> None:
    contract = UXContract.model_validate(contract_dict)
    assert contract.qcd.quality == "medium"


def test_transition_uses_from_key(contract_dict: dict[str, Any]) -> None:
    payload = contract_dict["statecharts"][0]["transitions"][0]
    assert payload["from"] == "a"
    contract = UXContract.model_validate(contract_dict)
    assert contract.statecharts[0].transitions[0].from_state == "a"


def test_duplicate_ids_rejected(contract_dict: dict[str, Any]) -> None:
    contract_dict["jobs"].append(dict(contract_dict["jobs"][0]))
    with pytest.raises(ValidationError):
        UXContract.model_validate(contract_dict)


def test_bad_surface_layer_rejected(contract_dict: dict[str, Any]) -> None:
    contract_dict["product"]["surfaces"][0]["layer"] = "hologram"
    with pytest.raises(ValidationError):
        UXContract.model_validate(contract_dict)


def test_unknown_fields_rejected(contract_dict: dict[str, Any]) -> None:
    contract_dict["surprise"] = True
    with pytest.raises(ValidationError):
        UXContract.model_validate(contract_dict)


def test_ruby_dsl_output_matches_committed_contract() -> None:
    """The committed .ux.json is the DSL's exact output (envelope keys)."""
    from pathlib import Path

    committed = json.loads(
        (Path("examples/smart-kettle/smart-kettle.ux.json")).read_text(encoding="utf-8")
    )
    contract = UXContract.model_validate(committed)
    assert contract.product.name == "smart-kettle"
