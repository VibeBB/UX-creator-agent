"""Boundary and decision-table tests for the deterministic UX gates.

Techniques follow docs/test-coverage.md: 3-value boundaries (below / on /
above) for touch-target size and feedback latency budgets, a decision
table for latency x progress indicator, and algebraic properties of the
WCAG contrast ratio.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path
from typing import Any

import pytest

from ux_creator.contract import UXContract
from ux_creator.gates import MIN_TARGET_MM, contrast_ratio, run_gates


def _check(contract_dict: dict[str, Any], check_id: str, **extra: Any) -> Any:
    contract = UXContract.model_validate({**contract_dict, **extra})
    report = run_gates(contract, Path.cwd())
    return next(c for c in report.checks if c.id == check_id)


def _below(value: float) -> float:
    return math.nextafter(value, -math.inf)


def _above(value: float) -> float:
    return math.nextafter(value, math.inf)


# --------------------------------------------------------- target size


@pytest.mark.parametrize("axis", ["width_mm", "height_mm"])
@pytest.mark.parametrize(
    ("size", "status"),
    [(_below(MIN_TARGET_MM), "fail"), (MIN_TARGET_MM, "pass"), (_above(MIN_TARGET_MM), "pass")],
)
def test_target_size_three_value_boundary(
    contract_dict: dict[str, Any], axis: str, size: float, status: str
) -> None:
    control = {"id": "b1", "surface": "btn", "kind": "button", "width_mm": 20.0, "height_mm": 20.0}
    control[axis] = size
    check = _check(contract_dict, "hig.target_size", controls=[control])
    assert check.status == status
    assert check.measured == size


# Decision table: kind x which dimensions are declared.
@pytest.mark.parametrize(
    ("kind", "dims", "status", "detail"),
    [
        ("button", {"width_mm": 5.0}, "fail", "undersized"),
        ("dial", {"height_mm": 5.0}, "fail", "undersized"),
        ("switch", {"width_mm": 5.0, "height_mm": 9.0}, "fail", "undersized"),
        ("touch", {}, "pass", "no sized controls"),
        ("button", {"width_mm": 9.0}, "pass", "no undersized controls"),
    ],
)
def test_target_size_decision_table(
    contract_dict: dict[str, Any], kind: str, dims: dict[str, float], status: str, detail: str
) -> None:
    control = {"id": "c1", "surface": "btn", "kind": kind, **dims}
    check = _check(contract_dict, "hig.target_size", controls=[control])
    assert check.status == status
    assert detail in check.detail


# ------------------------------------------------------ feedback latency


def _feedback(latency: int, progress: bool) -> dict[str, Any]:
    return {
        "id": "f1",
        "trigger": "btn",
        "surface": "btn",
        "modality": "visual",
        "latency_ms": latency,
        "progress_indicator": progress,
    }


# Decision table: latency band x progress indicator.
@pytest.mark.parametrize(
    ("latency", "progress", "status"),
    [
        (0, False, "pass"),
        (999, False, "pass"),
        (1000, False, "pass"),
        (1001, False, "fail"),
        (1001, True, "pass"),
        (9999, True, "pass"),
        (10000, True, "pass"),
        (10001, True, "fail"),
        (10001, False, "fail"),
    ],
)
def test_feedback_latency_decision_table(
    contract_dict: dict[str, Any], latency: int, progress: bool, status: str
) -> None:
    check = _check(
        contract_dict, "feedback.latency_budget", feedback=[_feedback(latency, progress)]
    )
    assert check.status == status
    assert check.measured == float(latency)


def test_no_feedback_reports_no_measurement(contract_dict: dict[str, Any]) -> None:
    check = _check(contract_dict, "feedback.latency_budget", feedback=[])
    assert check.status == "pass"
    assert check.measured is None


# ------------------------------------------------------ contrast ratio

SAMPLES = ["#000000", "#FFFFFF", "#777777", "#0057D9", "#0A0A0A", "#FF0000", "#00FF00", "#123456"]


def test_contrast_ratio_is_symmetric_and_bounded() -> None:
    for fg, bg in itertools.product(SAMPLES, repeat=2):
        ratio = contrast_ratio(fg, bg)
        assert ratio == pytest.approx(contrast_ratio(bg, fg))
        assert 1.0 - 1e-12 <= ratio <= 21.0 + 1e-12
    assert all(contrast_ratio(c, c) == pytest.approx(1.0) for c in SAMPLES)


def test_contrast_against_white_is_monotone_in_grey_level() -> None:
    greys = [f"#{level:02X}{level:02X}{level:02X}" for level in range(256)]
    ratios = [contrast_ratio(grey, "#FFFFFF") for grey in greys]
    assert all(later < earlier for earlier, later in itertools.pairwise(ratios))


def test_srgb_linearisation_is_continuous_at_the_knee() -> None:
    # Channel value 10/255 sits just above the 0.03928 knee and 9/255 just below.
    low = contrast_ratio("#090909", "#000000")
    high = contrast_ratio("#0A0A0A", "#000000")
    assert 1.0 < low < high < 1.1


@pytest.mark.parametrize(
    ("fg", "large", "status"),
    [
        ("#767676", False, "pass"),  # 4.54:1
        ("#777777", False, "fail"),  # 4.48:1
        ("#777777", True, "pass"),
        ("#999999", True, "fail"),  # 2.85:1
    ],
)
def test_text_contrast_threshold_by_text_size(
    contract_dict: dict[str, Any], fg: str, large: bool, status: str
) -> None:
    control = {"id": "t1", "surface": "btn", "fg": fg, "bg": "#FFFFFF", "large_text": large}
    assert _check(contract_dict, "hig.contrast", controls=[control]).status == status
