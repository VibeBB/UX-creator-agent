"""SLP v2 UX requests from the producer to sister agents."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .contract import UXContract
from .records import tree_sha256
from .sisters import PRODUCT_STAGES, SHA256, SLUG, TARGET_AGENTS, ProductStage, TargetAgent
from .workspace import workspace_path

SCHEMA_VERSION = 2
SYSTEM = "ux-creator"
JOB_ID = re.compile(r"\b[a-z][a-z0-9_]*\b")


def _relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value.strip()
        or value != value.strip()
        or "\\" in value
        or path.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or ".." in path.parts
    ):
        raise ValueError("path must be a normalized workspace-relative path")
    return path.as_posix()


class InputRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=SHA256.pattern)


class UXRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[2] = SCHEMA_VERSION
    system: Literal["ux-creator"] = SYSTEM
    id: str = Field(pattern=SLUG.pattern)
    target_agent: TargetAgent
    stage: ProductStage
    risk: Literal["low", "high"]
    purpose: str = Field(min_length=20)
    rationale: str = ""
    requested_changes: list[str] = Field(min_length=1)
    inputs: list[InputRef] = Field(default_factory=list[InputRef])
    expected_deliverables: list[str] = Field(min_length=1)
    acceptance: list[str] = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list[str])
    created_at: str

    @field_validator("purpose")
    @classmethod
    def _purpose_is_meaningful(cls, value: str) -> str:
        if len(value.strip()) < 20:
            raise ValueError("purpose must have at least 20 non-whitespace characters")
        return value

    @field_validator("requested_changes", "expected_deliverables", "acceptance")
    @classmethod
    def _items_are_nonblank(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("list entries must not be blank")
        return values

    @field_validator("created_at")
    @classmethod
    def _timestamp_is_aware(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("created_at must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value

    @model_validator(mode="after")
    def _references_are_valid(self) -> UXRequest:
        if self.risk == "high" and not self.rationale.strip():
            raise ValueError("high-risk requests require a non-blank rationale")
        input_paths = [item.path for item in self.inputs]
        if len(input_paths) != len(set(input_paths)):
            raise ValueError("inputs must have unique paths")
        if len(self.depends_on) != len(set(self.depends_on)):
            raise ValueError("depends_on must have unique ids")
        for dependency in self.depends_on:
            if not SLUG.fullmatch(dependency):
                raise ValueError(f"invalid dependency id {dependency!r}")
            if dependency == self.id:
                raise ValueError("depends_on cannot include the request's own id")
        return self


def build_request(
    contract: UXContract,
    *,
    id: str,
    target_agent: str,
    stage: ProductStage,
    risk: Literal["low", "high"],
    purpose: str,
    rationale: str,
    requested_changes: Sequence[str],
    inputs: Sequence[str],
    expected_deliverables: Sequence[str],
    acceptance: Sequence[str],
    workspace: Path,
    depends_on: Sequence[str] = (),
    now: datetime | None = None,
) -> UXRequest:
    if target_agent not in TARGET_AGENTS:
        raise ValueError(f"unknown target_agent {target_agent!r}; expected one of {TARGET_AGENTS}")
    if stage not in PRODUCT_STAGES:
        raise ValueError(f"unknown stage {stage!r}; expected one of {PRODUCT_STAGES}")
    if risk == "high":
        job_ids = {job.id for job in contract.jobs}
        cited = {token for token in JOB_ID.findall(rationale.lower())} & job_ids
        if not cited:
            raise ValueError(
                "high-risk requests must cite at least one job id in the rationale "
                f"(declared jobs: {sorted(job_ids)})"
            )
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("created_at must include a timezone")
    refs: list[InputRef] = []
    for value in inputs:
        relative = _relative_path(value)
        path = workspace_path(relative, workspace)
        if not path.exists():
            raise ValueError(f"request input does not exist: {relative}")
        refs.append(InputRef(path=relative, sha256=tree_sha256(path)))
    return UXRequest(
        id=id,
        target_agent=target_agent,
        stage=stage,
        risk=risk,
        purpose=purpose,
        rationale=rationale,
        requested_changes=list(requested_changes),
        inputs=refs,
        expected_deliverables=list(expected_deliverables),
        acceptance=list(acceptance),
        depends_on=list(depends_on),
        created_at=moment.isoformat(),
    )


def write_request(request: UXRequest, liaison_dir: Path, *, replace: bool = False) -> Path:
    liaison_dir.mkdir(parents=True, exist_ok=True)
    path = liaison_dir / f"{request.id}.ux-request.json"
    content = json.dumps(request.model_dump(), indent=2, sort_keys=True) + "\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return path
        if not replace:
            raise FileExistsError(f"refusing to overwrite a different request: {path}")
    path.write_text(content, encoding="utf-8")
    return path


def load_request(path: Path) -> UXRequest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    request = UXRequest.model_validate(payload)
    if not path.name.endswith(".ux-request.json"):
        raise ValueError(f"request filename must end in .ux-request.json: {path.name}")
    if path.name.removesuffix(".ux-request.json") != request.id:
        raise ValueError(f"request filename id does not match request id: {path.name}")
    return request
