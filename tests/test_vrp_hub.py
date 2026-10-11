from __future__ import annotations

from pathlib import Path
from typing import Any

from ux_creator import vrp_hub


def _concern(system: str, about: str, severity: str = "warning", n: int = 1) -> dict[str, Any]:
    return {"ref": f"{system}:e{n}#c{n}", "system": system, "about": about, "severity": severity}


def _digest(**parts: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "systems": {},
        "open_concerns": [],
        "disputes": [],
        "unacknowledged_reads": [],
        "insights": [],
        "review_disagreements": [],
        "songs": [],
    }
    return base | parts


def test_no_cycle_for_one_way_concerns() -> None:
    digest = _digest(open_concerns=[_concern("ux", "mech"), _concern("mech", "circuit")])
    assert vrp_hub.concern_cycles(digest) == []


def test_two_way_ping_pong_is_a_cycle() -> None:
    digest = _digest(
        open_concerns=[_concern("mech", "circuit", n=1)],
        disputes=[{"system": "circuit", "target": "mech:e1", "event_id": "e2"}],
    )
    cycles = vrp_hub.concern_cycles(digest)
    assert [c["systems"] for c in cycles] == [["circuit", "mech"]]
    assert cycles[0]["evidence"][0] == {
        "from": "circuit",
        "to": "mech",
        "refs": ["dispute mech:e1"],
    }


def test_three_sister_ring_is_reported_once() -> None:
    digest = _digest(
        open_concerns=[
            _concern("ux", "mech", n=1),
            _concern("mech", "circuit", n=2),
            _concern("circuit", "ux", n=3),
        ]
    )
    cycles = vrp_hub.concern_cycles(digest)
    assert [c["systems"] for c in cycles] == [["circuit", "ux", "mech"]]


def test_self_concerns_never_form_a_cycle() -> None:
    digest = _digest(open_concerns=[_concern("ux", "ux"), _concern("ux", "None")])
    assert vrp_hub.concern_cycles(digest) == []


def test_aggregate_counts_raised_and_owned_by_severity() -> None:
    digest = _digest(
        systems={"ux": {"integrity": "ok"}},
        open_concerns=[_concern("ux", "mech", "error"), _concern("wire", "mech", "info")],
        unacknowledged_reads=[{"reader": "mech", "ref": "ux:e1"}],
        insights=[
            {"ref": "ux:e1#i1", "target": "mech", "status": "tried"},
            {"ref": "ux:e1#i2", "target": "mech", "status": "adopted"},
        ],
        review_disagreements=[{"system": "ux"}],
    )
    table = vrp_hub.aggregate(digest)
    assert table["mech"]["concerns_owned"] == {"error": 1, "warning": 0, "info": 1}
    assert table["ux"]["concerns_raised"]["error"] == 1
    assert table["mech"]["unanswered_reads"] == 1
    assert table["mech"]["open_insights"] == 1
    assert table["ux"]["review_splits"] == 1


def test_hub_on_empty_workspace_is_clear(tmp_path: Path) -> None:
    result = vrp_hub.hub(tmp_path)
    assert result["status"] == "clear"
    assert result["advisory"] is True
    assert result["cycles"] == []


def test_hub_flags_a_broken_sister_log(tmp_path: Path) -> None:
    log = tmp_path / "observations" / "mech" / "impressions.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text("{not json\n", encoding="utf-8")
    result = vrp_hub.hub(tmp_path)
    assert result["status"] == "attention"
    assert result["broken_logs"] == ["mech"]
