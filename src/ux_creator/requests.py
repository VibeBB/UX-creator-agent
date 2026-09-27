"""ux-request.json — structured change requests from ux-creator to siblings.

A request is a plain JSON file in the workspace; the sibling agent reads
it like any other artifact (ADR-0003). `risk: high` requests (tooling,
board, firmware architecture) are never auto-sent: they must carry a
rationale that cites at least one job id from the contract.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .contract import UXContract

SCHEMA_VERSION = 1
SYSTEM = "ux-creator"
TARGET_AGENTS = ("wire", "mech", "circuit", "bard")
_JOB_ID = re.compile(r"\b[a-z][a-z0-9_]*\b")


class UXRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = SCHEMA_VERSION
    system: Literal["ux-creator"] = SYSTEM
    target_agent: str = Field(min_length=1)
    risk: Literal["low", "high"]
    rationale: str = ""
    requested_changes: list[str] = Field(min_length=1)


def build_request(
    contract: UXContract,
    *,
    target_agent: str,
    risk: Literal["low", "high"],
    rationale: str,
    requested_changes: list[str],
) -> UXRequest:
    if target_agent not in TARGET_AGENTS:
        raise ValueError(f"unknown target_agent {target_agent!r}; expected one of {TARGET_AGENTS}")
    if risk == "high":
        job_ids = {j.id for j in contract.jobs}
        cited = {tok for tok in _JOB_ID.findall(rationale.lower())} & job_ids
        if not cited:
            raise ValueError(
                "high-risk requests must cite at least one job id in the rationale "
                f"(declared jobs: {sorted(job_ids)})"
            )
    return UXRequest(
        target_agent=target_agent,
        risk=risk,
        rationale=rationale,
        requested_changes=requested_changes,
    )


def write_request(request: UXRequest, out_dir: Path, name: str = "ux-request") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.ux-request.json"
    path.write_text(
        json.dumps(request.model_dump(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def request_to_dict(request: UXRequest) -> dict[str, Any]:
    return request.model_dump()
