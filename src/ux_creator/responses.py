"""SLP v2 sister responses and fail-closed liaison reconciliation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .records import tree_sha256
from .requests import UXRequest, load_request
from .sisters import SHA256, SLUG, ProductStage, TargetAgent
from .workspace import workspace_path

ResponseStatus = Literal["accepted", "in_progress", "done", "rejected", "deferred", "needs_info"]
LiaisonState = Literal["open", "answered", "mismatched", "stale", "broken", "blocked", "circular"]
ALL_STATES: tuple[LiaisonState, ...] = (
    "open",
    "answered",
    "mismatched",
    "stale",
    "broken",
    "blocked",
    "circular",
)
ALL_STATUSES: tuple[ResponseStatus, ...] = (
    "accepted",
    "in_progress",
    "done",
    "rejected",
    "deferred",
    "needs_info",
)


class ArtifactRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=SHA256.pattern)


class GateVerdict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    gate: str = Field(min_length=1)
    verdict: Literal["pass", "fail", "unknown"]


class UXResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[2] = 2
    system: Literal["ux-creator"] = "ux-creator"
    request: str = Field(pattern=SLUG.pattern)
    responder: TargetAgent
    status: ResponseStatus
    reason: str = ""
    input_hashes: dict[str, str] = Field(default_factory=dict[str, str])
    artifacts: list[ArtifactRef] = Field(default_factory=list[ArtifactRef])
    gate_verdicts: list[GateVerdict] = Field(default_factory=list[GateVerdict])
    decision_refs: list[str] = Field(default_factory=list[str])
    impression_refs: list[str] = Field(default_factory=list[str])
    questions_for_user: list[str] = Field(default_factory=list[str])
    responded_at: str

    @field_validator("input_hashes")
    @classmethod
    def _input_hashes_are_valid(cls, values: dict[str, str]) -> dict[str, str]:
        for path, digest in values.items():
            if not SHA256.fullmatch(digest):
                raise ValueError(f"invalid SHA256 for response input {path!r}")
        return values

    @field_validator("decision_refs")
    @classmethod
    def _decision_refs_are_valid(cls, values: list[str]) -> list[str]:
        if any(not SHA256.fullmatch(value) for value in values):
            raise ValueError("decision_refs must contain SHA256 event ids")
        return values

    @field_validator("impression_refs")
    @classmethod
    def _impression_refs_are_valid(cls, values: list[str]) -> list[str]:
        if any(not SHA256.fullmatch(value) for value in values):
            raise ValueError("impression_refs must contain SHA256 event ids")
        return values

    @field_validator("questions_for_user")
    @classmethod
    def _questions_are_nonblank(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("questions_for_user must not contain blank values")
        return values

    @field_validator("responded_at")
    @classmethod
    def _timestamp_is_aware(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("responded_at must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("responded_at must include a timezone")
        return value

    @model_validator(mode="after")
    def _status_has_valid_evidence(self) -> UXResponse:
        if self.status not in ("accepted", "in_progress") and len(self.reason.strip()) < 20:
            raise ValueError("reason must have at least 20 non-whitespace characters")
        if self.status == "done" and any(
            verdict.verdict != "pass" for verdict in self.gate_verdicts
        ):
            raise ValueError("done responses cannot contain fail or unknown gate verdicts")
        return self


class LiaisonEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    request: str
    target_agent: TargetAgent
    stage: ProductStage
    risk: Literal["low", "high"]
    state: LiaisonState
    problems: list[str] = Field(default_factory=list[str])
    depends_on: list[str] = Field(default_factory=list[str])
    response_status: ResponseStatus | None = None
    responder: TargetAgent | None = None
    reason: str = ""
    response_path: str = ""
    gate_verdicts: list[GateVerdict] = Field(default_factory=list[GateVerdict])
    decision_refs: list[str] = Field(default_factory=list[str])
    impression_refs: list[str] = Field(default_factory=list[str])
    questions_for_user: list[str] = Field(default_factory=list[str])
    responded_at: str = ""


class LiaisonStatus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[2] = 2
    entries: list[LiaisonEntry]
    orphans: list[str]
    malformed: list[str]
    summary: dict[LiaisonState, int]


def _read_event_ids(workspace: Path, plugin: str, filename: str) -> set[str]:
    event_ids: set[str] = set()
    try:
        path = workspace_path(Path("observations") / plugin / filename, workspace)
        if not path.is_file():
            return event_ids
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError, ValueError):
        return event_ids
    for line in lines:
        try:
            payload: object = json.loads(line)
        except ValueError:
            continue
        if isinstance(payload, Mapping):
            event_id = cast(Mapping[str, object], payload).get("event_id")
            if isinstance(event_id, str):
                event_ids.add(event_id)
    return event_ids


def _input_problems(request: UXRequest, response: UXResponse, workspace: Path) -> list[str]:
    problems: list[str] = []
    for item in request.inputs:
        try:
            path = workspace_path(item.path, workspace)
            current = tree_sha256(path) if path.exists() else None
        except (OSError, ValueError):
            current = None
        if current != item.sha256:
            problems.append(f"input {item.path} is missing or changed")
        response_hash = response.input_hashes.get(item.path)
        if response_hash != item.sha256:
            problems.append(f"response input hash is missing or changed for {item.path}")
    return problems


def _response_problems(response: UXResponse, workspace: Path) -> list[str]:
    broken: list[str] = []
    for artifact in response.artifacts:
        try:
            path = workspace_path(artifact.path, workspace)
            current = tree_sha256(path) if path.exists() else None
        except (OSError, ValueError):
            current = None
        if current != artifact.sha256:
            broken.append(f"artifact {artifact.path} is missing or changed")
    decisions = _read_event_ids(workspace, response.responder, "decisions.jsonl")
    missing_decisions = sorted(set(response.decision_refs) - decisions)
    if missing_decisions:
        broken.append(f"decision refs not found: {', '.join(missing_decisions)}")
    impressions = _read_event_ids(workspace, response.responder, "impressions.jsonl")
    impressions |= _read_event_ids(workspace, response.responder, "vision-reviews.jsonl")
    missing_impressions = sorted(set(response.impression_refs) - impressions)
    if missing_impressions:
        broken.append(f"impression refs not found: {', '.join(missing_impressions)}")
    return broken


def _load_requests(liaison_dir: Path, workspace: Path) -> tuple[dict[str, UXRequest], list[str]]:
    requests: dict[str, UXRequest] = {}
    malformed: list[str] = []
    for path in sorted(liaison_dir.glob("*.ux-request.json")):
        try:
            request = load_request(workspace_path(path, workspace))
        except (OSError, UnicodeError, ValueError) as exc:
            malformed.append(f"{path}: {str(exc).splitlines()[0]}")
            continue
        requests[request.id] = request
    return requests, malformed


def _load_responses(
    liaison_dir: Path, workspace: Path
) -> tuple[dict[str, tuple[Path, UXResponse]], list[str]]:
    responses: dict[str, tuple[Path, UXResponse]] = {}
    malformed: list[str] = []
    for path in sorted(liaison_dir.glob("*.ux-response.json")):
        try:
            safe_path = workspace_path(path, workspace)
            payload = json.loads(safe_path.read_text(encoding="utf-8"))
            response = UXResponse.model_validate(payload)
            if safe_path.name.removesuffix(".ux-response.json") != response.request:
                raise ValueError("response filename id does not match request id")
        except (OSError, UnicodeError, ValueError) as exc:
            malformed.append(f"{path}: {str(exc).splitlines()[0]}")
            continue
        responses[response.request] = (safe_path, response)
    return responses, malformed


def _cycle_members(requests: Mapping[str, UXRequest]) -> set[str]:
    state: dict[str, int] = {}
    stack: list[str] = []
    members: set[str] = set()

    def visit(request_id: str) -> None:
        state[request_id] = 1
        stack.append(request_id)
        request = requests[request_id]
        for dependency in request.depends_on:
            if dependency not in requests:
                continue
            if state.get(dependency, 0) == 1:
                members.update(stack[stack.index(dependency) :])
            elif state.get(dependency, 0) == 0:
                visit(dependency)
        stack.pop()
        state[request_id] = 2

    for request_id in sorted(requests):
        if state.get(request_id, 0) == 0:
            visit(request_id)
    return members


def liaison_status(liaison_dir: Path, workspace: Path) -> LiaisonStatus:
    try:
        safe_liaison_dir = workspace_path(liaison_dir, workspace)
    except (OSError, ValueError) as exc:
        return LiaisonStatus(
            entries=[],
            orphans=[],
            malformed=[f"{liaison_dir}: {exc}"],
            summary={state: 0 for state in ALL_STATES},
        )
    requests, malformed_requests = _load_requests(safe_liaison_dir, workspace)
    responses, malformed_responses = _load_responses(safe_liaison_dir, workspace)
    malformed = sorted(malformed_requests + malformed_responses)
    request_ids = set(requests)
    orphans = sorted(
        str(path)
        for request_id, (path, _response) in responses.items()
        if request_id not in request_ids
    )
    cycles = _cycle_members(requests)
    malformed_response_ids = {
        Path(item.partition(": ")[0]).name.removesuffix(".ux-response.json")
        for item in malformed_responses
    }
    state_by_id: dict[str, LiaisonState] = {}
    entries_by_id: dict[str, LiaisonEntry] = {}

    def evaluate(request_id: str) -> LiaisonState:
        if request_id in state_by_id:
            return state_by_id[request_id]
        request = requests[request_id]
        problems: list[str] = []
        if request_id in cycles:
            problems.append("request is a member of a dependency cycle")
        response_tuple = responses.get(request_id)
        if response_tuple is None:
            if request_id in malformed_response_ids:
                problems.append("response file is malformed")
            dependency_states: list[tuple[str, LiaisonState | None]] = []
            for dependency in request.depends_on:
                if dependency in requests:
                    dependency_state = (
                        "circular"
                        if request_id in cycles and dependency in cycles
                        else evaluate(dependency)
                    )
                    dependency_states.append((dependency, dependency_state))
                else:
                    dependency_states.append((dependency, None))
            for dependency, dependency_state in dependency_states:
                if dependency_state is None:
                    problems.append(f"dependency {dependency} does not exist")
                elif dependency_state != "answered":
                    problems.append(f"dependency {dependency} is {dependency_state}")
            if request_id in cycles:
                state: LiaisonState = "circular"
            elif any(
                dependency_state is None or dependency_state != "answered"
                for _dependency, dependency_state in dependency_states
            ):
                state = "blocked"
            else:
                state = "open"
            entry = LiaisonEntry(
                request=request_id,
                target_agent=request.target_agent,
                stage=request.stage,
                risk=request.risk,
                state=state,
                problems=problems,
                depends_on=request.depends_on,
            )
        else:
            response_path, response = response_tuple
            input_problems = _input_problems(request, response, workspace)
            broken_problems = _response_problems(response, workspace)
            problems.extend(input_problems)
            problems.extend(broken_problems)
            if response.responder != request.target_agent:
                problems.append(
                    f"responder {response.responder} does not match target {request.target_agent}"
                )
            if request_id in cycles:
                state = "circular"
            elif response.responder != request.target_agent:
                state = "mismatched"
            elif input_problems:
                state = "stale"
            elif broken_problems:
                state = "broken"
            else:
                state = "answered"
            entry = LiaisonEntry(
                request=request_id,
                target_agent=request.target_agent,
                stage=request.stage,
                risk=request.risk,
                state=state,
                problems=problems,
                depends_on=request.depends_on,
                response_status=response.status,
                responder=response.responder,
                reason=response.reason,
                response_path=str(response_path),
                gate_verdicts=response.gate_verdicts,
                decision_refs=response.decision_refs,
                impression_refs=response.impression_refs,
                questions_for_user=response.questions_for_user,
                responded_at=response.responded_at,
            )
        state_by_id[request_id] = state
        entries_by_id[request_id] = entry
        return state

    for request_id in sorted(requests):
        evaluate(request_id)
    entries = [entries_by_id[request_id] for request_id in sorted(entries_by_id)]
    summary: dict[LiaisonState, int] = {
        state: sum(entry.state == state for entry in entries) for state in ALL_STATES
    }
    return LiaisonStatus(
        entries=entries,
        orphans=orphans,
        malformed=malformed,
        summary=summary,
    )


def load_response_records(liaison_dir: Path, workspace: Path) -> list[tuple[Path, UXResponse]]:
    """Load valid responses in filename order, including orphan responses."""
    try:
        safe_liaison_dir = workspace_path(liaison_dir, workspace)
    except (OSError, ValueError):
        return []
    responses, _malformed = _load_responses(safe_liaison_dir, workspace)
    return [responses[key] for key in sorted(responses)]
