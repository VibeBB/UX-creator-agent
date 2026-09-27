"""Typed advisory review records (L2 only — never verdicts).

A vision-capable reviewer writes `review-visual-<slug>.advisory.json`
next to `ux-report.json`; `parse_visual_review` validates the detail so a
malformed model answer can never masquerade as a record (returns `None`).
Same contract shape as wire's `src/wire/advisory.py`.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

VISION_REVIEW_TOOL = "vision_review"
IMPRESSION_MIN_LENGTH = 240
_SENTENCE_MARKS = "。.!?"

VisualChecklist = Literal["journey_map", "statechart", "wireframe", "intake_image"]
VisualFindingCategory = Literal[
    "missing_touchpoint",
    "broken_flow",
    "unreachable_state",
    "label_collision",
    "text_outside_frame",
    "illegible",
    "ambiguous_notation",
    "missing_element",
    "design_intent",
    "other",
]


class VisualFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: VisualFindingCategory
    severity: Literal["info", "minor", "major"] = "info"
    where: str = ""
    observation: str = Field(min_length=1)
    suggestion: str = ""


class VisualReviewDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checklist: VisualChecklist
    image_path: str = Field(min_length=1)
    image_sha256: str = Field(min_length=1)
    model: str = ""
    findings: list[VisualFinding] = Field(default_factory=list[VisualFinding])


class AdvisoryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str = VISION_REVIEW_TOOL
    stage: str = "review"
    status: Literal["ok", "error", "not_applicable"]
    summary: str = ""
    artifacts: list[str] = Field(default_factory=list[str])
    detail: VisualReviewDetail | dict[str, Any] | None = None


def _sentence_count(text: str) -> int:
    return len([m for m in _SENTENCE_MARKS if m in text]) or (1 if text.strip() else 0)


def parse_visual_review(payload: dict[str, Any]) -> AdvisoryResult | None:
    """Validate a visual-review record; None when malformed (fail-closed)."""
    try:
        record = AdvisoryResult.model_validate(payload)
    except ValidationError:
        return None
    if record.status == "ok":
        if (
            len(record.summary.strip()) < IMPRESSION_MIN_LENGTH
            or _sentence_count(record.summary) < 2
        ):
            return None
        if not isinstance(record.detail, VisualReviewDetail):
            return None
    return record


def write_visual_review(
    image: Path,
    checklist: VisualChecklist,
    summary: str,
    findings: list[VisualFinding],
    model: str = "",
) -> Path:
    """Compute the image sha256 and write the sibling advisory record."""
    slug = re.sub(r"[^a-z0-9]+", "-", image.stem.lower()).strip("-") or "image"
    detail = VisualReviewDetail(
        checklist=checklist,
        image_path=str(image),
        image_sha256=f"sha256:{hashlib.sha256(image.read_bytes()).hexdigest()}",
        model=model,
        findings=findings,
    )
    record = AdvisoryResult(status="ok", summary=summary, artifacts=[str(image)], detail=detail)
    path = image.parent / f"review-visual-{slug}.advisory.json"
    import json

    path.write_text(
        json.dumps(record.model_dump(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path
