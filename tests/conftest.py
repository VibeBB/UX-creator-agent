from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ux_creator.contract import UXContract

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "examples" / "smart-kettle" / "smart-kettle.ux.json"


@pytest.fixture()
def example_contract() -> UXContract:
    return UXContract.model_validate(json.loads(EXAMPLE.read_text(encoding="utf-8")))


@pytest.fixture()
def contract_dict() -> dict[str, Any]:
    """Minimal passing contract payload."""
    return {
        "schema_version": 1,
        "system": "ux-creator",
        "product": {
            "name": "demo",
            "surfaces": [{"id": "btn", "layer": "hardware"}],
        },
        "core_experience": "it just works",
        "personas": [{"id": "p1", "goals": ["g"]}],
        "jobs": [
            {
                "id": "j1",
                "functional": "f",
                "emotional": "e",
                "social": "s",
                "importance": 8,
                "satisfaction": 5,
            }
        ],
        "journeys": [
            {
                "id": "jn",
                "stages": [
                    {
                        "id": "s1",
                        "touchpoints": ["btn"],
                        "emotion": 4,
                        "surfaces": ["btn"],
                    }
                ],
            }
        ],
        "statecharts": [
            {
                "id": "sc",
                "states": [
                    {"id": "a", "initial": True},
                    {"id": "b", "final": True},
                ],
                "transitions": [{"from": "a", "event": "go", "to": "b"}],
            }
        ],
    }
