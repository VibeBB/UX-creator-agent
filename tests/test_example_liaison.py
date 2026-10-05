"""Keep checked-in SLP v2 examples hash-consistent and parseable."""

from __future__ import annotations

from pathlib import Path

from ux_creator.responses import liaison_status

ROOT = Path(__file__).resolve().parents[1]


def test_smart_kettle_example_requests_and_responses_reconcile() -> None:
    examples = (
        (ROOT, ROOT / "examples/smart-kettle"),
        (
            ROOT / "examples/smart-kettle-product",
            ROOT / "examples/smart-kettle-product/requests",
        ),
    )
    statuses = [liaison_status(liaison_dir, workspace) for workspace, liaison_dir in examples]
    for status in statuses:
        assert status.malformed == []
        assert status.orphans == []
        assert all(entry.state not in ("stale", "broken", "mismatched") for entry in status.entries)
    assert {entry.request: entry.state for entry in statuses[0].entries} == {
        "smart-kettle-app-onboard-tour": "open",
        "smart-kettle-led-brightness": "answered",
    }
    assert {entry.request: entry.state for entry in statuses[1].entries} == {
        "smart-kettle-boil-key": "open",
        "smart-kettle-cues": "answered",
    }
