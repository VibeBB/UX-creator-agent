"""Collect SHA-bound work evidence; native SDK tasks own execution and retries."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from .contract import load_contract
from .delegation import delegation_brief
from .gates import run_gates
from .records import tree_sha256
from .requests import UXRequest
from .responses import UXResponse, liaison_status
from .sisters import TargetAgent
from .workspace import workspace_path, workspace_root

_SHA = r"^[0-9a-f]{64}$"
_SLUG = r"^[a-z0-9][a-z0-9_-]{0,63}$"


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class WorkStep(_Strict):
    id: str = Field(pattern=_SLUG)
    kind: Literal["design", "liaison", "domain"]
    inputs: list[str] = Field(default_factory=list[str], max_length=100)
    output_contract: str | None = None
    request_path: str | None = None
    target_agent: TargetAgent | None = None
    depends_on: list[str] = Field(default_factory=list[str], max_length=100)

    @model_validator(mode="after")
    def _kind_fields(self) -> WorkStep:
        if (self.kind == "design") != (self.output_contract is not None):
            raise ValueError("only design requires output_contract")
        if (self.kind != "design") != (self.request_path is not None):
            raise ValueError("liaison/domain require request_path; design forbids it")
        if (self.kind != "design") != (self.target_agent is not None):
            raise ValueError("liaison/domain require target_agent; design forbids it")
        if len(self.inputs) != len(set(self.inputs)):
            raise ValueError("step inputs must be unique")
        if len(self.depends_on) != len(set(self.depends_on)):
            raise ValueError("step dependencies must be unique")
        return self


class ReportedUsage(_Strict):
    """Optional coordinator-reported counters, never a provider accounting claim."""

    native_iterations: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class WorkCheckpointInput(_Strict):
    action: Literal["create", "status", "start", "collect", "pause"]
    checkpoint_id: str = Field(pattern=_SLUG)
    session_id: str = Field(min_length=1)
    source_path: str | None = None
    steps: list[WorkStep] = Field(default_factory=list[WorkStep], max_length=100)
    liaison_dir: str | None = None
    attempt_budget: int | None = Field(default=None, ge=1, le=100)
    step_id: str | None = Field(default=None, pattern=_SLUG)
    attempt_id: str | None = Field(default=None, pattern=_SHA)
    child_session_id: str | None = Field(default=None, min_length=1)
    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    reported_usage: ReportedUsage | None = None

    @model_validator(mode="after")
    def _arguments(self) -> WorkCheckpointInput:
        for value in (self.session_id, self.child_session_id, self.reason):
            if value is not None and (not value.strip() or value != value.strip()):
                raise ValueError("session identities and reasons must be trimmed and nonblank")
        if self.action == "create":
            if not self.source_path or not self.steps:
                raise ValueError("create requires source_path and steps")
        elif (
            self.source_path is not None
            or self.steps
            or self.liaison_dir is not None
            or self.attempt_budget is not None
        ):
            raise ValueError(
                "only create accepts source_path, steps, liaison_dir or attempt_budget"
            )
        collecting = self.action in {"collect", "pause"}
        if collecting != (self.step_id is not None and self.attempt_id is not None):
            raise ValueError("collect/pause require step_id and attempt_id")
        if not collecting and (self.step_id is not None or self.attempt_id is not None):
            raise ValueError("only collect/pause accept step_id and attempt_id")
        if self.action == "collect" and self.child_session_id is None:
            raise ValueError("collect requires the native child_session_id")
        if (self.action == "pause") != (self.reason is not None):
            raise ValueError("only pause requires a reason")
        if not collecting and (
            self.child_session_id is not None or self.reported_usage is not None
        ):
            raise ValueError("child identity and reported usage belong to collect/pause")
        return self


class _Artifact(_Strict):
    path: str
    sha256: str = Field(pattern=_SHA)


class _Attempt(_Strict):
    id: str = Field(pattern=_SHA)
    child_session_id: str | None = None
    gap: str | None = None
    reported_usage: ReportedUsage | None = None


class _Step(_Strict):
    spec: WorkStep
    inputs: list[_Artifact]
    prepared: bool = False
    attempts: list[_Attempt] = Field(default_factory=list[_Attempt], max_length=2)
    active: bool = False
    evidence: list[_Artifact] = Field(default_factory=list[_Artifact])


class _Checkpoint(_Strict):
    schema_version: Literal[1] = 1
    id: str
    session_id: str
    source: _Artifact
    steps: list[_Step] = Field(min_length=1, max_length=100)
    liaison_dir: str
    attempt_budget: int = Field(ge=1, le=100)
    seal: str = Field(pattern=_SHA)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _artifact(value: str, base: Path) -> _Artifact:
    path = workspace_path(value, base)
    return _Artifact(path=path.relative_to(base).as_posix(), sha256=tree_sha256(path))


def _request(spec: WorkStep, base: Path) -> UXRequest:
    path = workspace_path(spec.request_path or "", base)
    return UXRequest.model_validate_json(path.read_text(encoding="utf-8"))


def _prepare(step: _Step, liaison_dir: str, base: Path) -> _Step:
    spec = step.spec
    inputs = [_artifact(path, base) for path in spec.inputs]
    if spec.request_path is not None:
        request = _request(spec, base)
        expected = workspace_path(f"{liaison_dir}/{request.id}.ux-request.json", base)
        if workspace_path(spec.request_path, base) != expected:
            raise ValueError("request_path must name the request ID in the run's liaison directory")
        if request.target_agent != spec.target_agent:
            raise ValueError("request target does not match the planned target_agent")
        inputs.append(_artifact(spec.request_path, base))
        for item in request.inputs:
            current = _artifact(item.path, base)
            if current.sha256 != item.sha256:
                raise ValueError(f"request input is missing or changed: {item.path}")
            inputs.append(current)
    if spec.output_contract in {item.path for item in inputs}:
        raise ValueError("a design output cannot overwrite its pinned inputs")
    return step.model_copy(
        update={"inputs": list({item.path: item for item in inputs}.values()), "prepared": True}
    )


def _step(spec: WorkStep, liaison_dir: str, base: Path) -> _Step:
    updates: dict[str, object] = {
        key: workspace_path(value, base).relative_to(base).as_posix()
        for key, value in (
            ("request_path", spec.request_path),
            ("output_contract", spec.output_contract),
        )
        if value is not None
    }
    updates["inputs"] = [
        workspace_path(path, base).relative_to(base).as_posix() for path in spec.inputs
    ]
    step = _Step(spec=WorkStep.model_validate({**spec.model_dump(), **updates}), inputs=[])
    return _prepare(step, liaison_dir, base) if not spec.depends_on else step


def _create(request: WorkCheckpointInput, base: Path) -> _Checkpoint:
    liaison = workspace_path(request.liaison_dir or "liaison", base).relative_to(base).as_posix()
    steps = [_step(spec, liaison, base) for spec in request.steps]
    prior: set[str] = set()
    for step in steps:
        if step.spec.id in prior or not set(step.spec.depends_on) <= prior:
            raise ValueError("step IDs must be unique and dependencies must precede their step")
        prior.add(step.spec.id)
    source = _artifact(request.source_path or "", base)
    outputs = [step.spec.output_contract for step in steps if step.spec.output_contract]
    pinned = {source.path, *(item.path for step in steps for item in step.inputs)}
    if len(outputs) != len(set(outputs)) or set(outputs) & pinned:
        raise ValueError("design outputs must be unique and separate from pinned inputs")
    return _Checkpoint(
        id=request.checkpoint_id,
        session_id=request.session_id,
        source=source,
        steps=steps,
        liaison_dir=liaison,
        attempt_budget=request.attempt_budget or 24,
        seal="0" * 64,
    )


def _evidence(step: _Step, state: _Checkpoint, base: Path) -> list[_Artifact]:
    spec = step.spec
    if spec.kind == "design":
        contract = load_contract(workspace_path(spec.output_contract or "", base))
        if run_gates(contract, base).verdict != "pass":
            raise ValueError("design gates are not pass for the current workspace")
        return [_artifact(spec.output_contract or "", base)]
    request = _request(spec, base)
    status = liaison_status(workspace_path(state.liaison_dir, base), base)
    if status.malformed:
        raise ValueError("liaison evidence is malformed: " + status.malformed[0])
    entries = {entry.request: entry for entry in status.entries}
    entry = entries.get(request.id)
    if entry is None or entry.state != "answered" or entry.response_status != "done":
        raise ValueError("liaison response must be answered, intact and done")
    if any(
        entries.get(dep) is None
        or entries[dep].state != "answered"
        or entries[dep].response_status != "done"
        for dep in request.depends_on
    ):
        raise ValueError("liaison dependencies must have done responses")
    if spec.kind == "domain" and not entry.gate_verdicts:
        raise ValueError("domain response requires reported deterministic gate verdicts")
    response = UXResponse.model_validate_json(
        workspace_path(entry.response_path, base).read_text(encoding="utf-8")
    )
    if not response.artifacts:
        raise ValueError("done response must retain at least one artifact")
    return [
        _artifact(entry.response_path, base),
        *[_artifact(item.path, base) for item in response.artifacts],
    ]


def _gaps(state: _Checkpoint, base: Path) -> list[str]:
    gaps: list[str] = []
    for item in [state.source, *(item for step in state.steps for item in step.inputs)]:
        try:
            if _artifact(item.path, base) != item:
                gaps.append(f"input changed: {item.path}")
        except (OSError, ValueError) as exc:
            gaps.append(f"input unavailable: {item.path}: {exc}")
    for step in state.steps:
        if not step.evidence:
            continue
        try:
            if _evidence(step, state, base) != step.evidence:
                gaps.append(f"collected evidence changed: {step.spec.id}")
        except (OSError, ValueError) as exc:
            gaps.append(f"collected evidence unknown: {step.spec.id}: {exc}")
    return gaps


def _save(path: Path, state: _Checkpoint) -> _Checkpoint:
    body = state.model_dump(mode="json", exclude={"seal"})
    state = _Checkpoint.model_validate({**body, "seal": _digest(body)})
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as f:
        temporary = Path(f.name)
        try:
            f.write(state.model_dump_json(indent=2) + "\n")
            f.flush()
            os.fsync(f.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    return state


def _brief(step: _Step, state: _Checkpoint, base: Path) -> dict[str, str]:
    if step.spec.kind == "design":
        brief = {
            "subagent_type": "ux-creator",
            "description": f"design step {step.spec.id}",
            "prompt": (
                f"Complete only design step {step.spec.id}. Author {step.spec.output_contract} "
                "through the UX authoring API and run its deterministic gates. "
                f"Read source {state.source.path} at SHA256 {state.source.sha256}."
            ),
        }
    else:
        brief = delegation_brief(_request(step.spec, base), state.liaison_dir)
    brief["prompt"] += (
        "\nUse a fresh native task_tool_set child without resume. Honor the agent definition's "
        "native iteration and budget limits and the SDK's provider retry/backoff. Do not add "
        "a retry loop or dispatch another checkpoint step. Return evidence paths or an explicit "
        "gap after cancellation, timeout, rate limiting or budget exhaustion. The coordinator "
        "collects evidence; do not edit the checkpoint or claim product acceptance. "
        f"Step inputs: {json.dumps([item.model_dump() for item in step.inputs], sort_keys=True)}"
    )
    return brief


def _start(state: _Checkpoint, base: Path) -> tuple[_Checkpoint, _Step | None]:
    if any(step.active for step in state.steps):
        raise ValueError("a native child is active; inspect it before collect/pause")
    if sum(len(step.attempts) for step in state.steps) >= state.attempt_budget:
        return state, None
    completed = {step.spec.id for step in state.steps if step.evidence}
    step = next((step for step in state.steps if not step.evidence), None)
    if step is None or len(step.attempts) >= 2 or not set(step.spec.depends_on) <= completed:
        return state, None
    if not step.prepared:
        step = _prepare(step, state.liaison_dir, base)
    attempt = _Attempt(
        id=_digest(
            [state.id, state.session_id, state.source.sha256, step.spec.id, len(step.attempts) + 1]
        )
    )
    updated = step.model_copy(update={"active": True, "attempts": [*step.attempts, attempt]})
    return _replace(state, updated), updated


def _replace(state: _Checkpoint, updated: _Step) -> _Checkpoint:
    return state.model_copy(
        update={
            "steps": [updated if step.spec.id == updated.spec.id else step for step in state.steps]
        }
    )


def _finish(state: _Checkpoint, request: WorkCheckpointInput, base: Path) -> _Checkpoint:
    step = next((step for step in state.steps if step.spec.id == request.step_id), None)
    if step is None or not step.attempts or step.attempts[-1].id != request.attempt_id:
        raise ValueError("step_id/attempt_id must identify the last reserved attempt")
    if step.evidence or any(other.active and other != step for other in state.steps):
        raise ValueError("the step is collected or a different native child is active")
    attempt = step.attempts[-1]
    child = request.child_session_id or attempt.child_session_id
    used = {
        item.child_session_id
        for other in state.steps
        for item in other.attempts
        if item.id != attempt.id and item.child_session_id
    }
    if child == state.session_id or (child and child in used):
        raise ValueError("each attempt requires a fresh child distinct from the coordinator")
    if attempt.child_session_id and child != attempt.child_session_id:
        raise ValueError("the attempt is bound to a different native child")
    if request.action == "pause" and not step.active:
        raise ValueError("only an active native child can be paused")
    evidence = _evidence(step, state, base) if request.action == "collect" else []
    updated = attempt.model_copy(
        update={
            "child_session_id": child,
            "gap": request.reason or attempt.gap,
            "reported_usage": request.reported_usage or attempt.reported_usage,
        }
    )
    return _replace(
        state,
        step.model_copy(
            update={
                "active": False,
                "attempts": [*step.attempts[:-1], updated],
                "evidence": evidence,
            }
        ),
    )


def _result(
    state: _Checkpoint, gaps: list[str], delegate: dict[str, str] | None
) -> dict[str, JsonValue]:
    pending = [step for step in state.steps if not step.evidence]
    attempts = sum(len(step.attempts) for step in state.steps)
    active = any(step.active for step in pending)
    exhausted = not active and (
        attempts >= state.attempt_budget or any(len(step.attempts) >= 2 for step in pending)
    )
    status = "blocked" if gaps or (pending and exhausted) else "pending"
    if not gaps and not pending:
        status = "collected"
    elif not gaps and any(step.active for step in pending):
        status = "active"
    return cast(
        dict[str, JsonValue],
        {
            **state.model_dump(mode="json", exclude={"seal"}),
            "scope": "work-evidence-collection",
            "status": status,
            "acceptance": "unknown",
            "workflow_completion": "unknown",
            "native_execution": "unknown",
            "usage_provenance": "coordinator-reported; absent counters remain unknown",
            "attempts_consumed": attempts,
            "remaining_steps": [step.spec.id for step in pending],
            "gaps": gaps
            + (
                ["attempt budget exhausted; collect existing evidence or stop"]
                if pending and exhausted
                else []
            ),
            "delegate": delegate,
        },
    )


def work_checkpoint(
    payload: dict[str, JsonValue], root: Path | None = None
) -> dict[str, JsonValue]:
    """Reserve bounded work or verify evidence without executing a child or solver."""
    request = WorkCheckpointInput.model_validate(payload)
    native = os.environ.get("OPENHANDS_SESSION_ID")
    if native and native != request.session_id:
        raise ValueError("session_id does not match OPENHANDS_SESSION_ID")
    base = (root or workspace_root()).resolve()
    path = workspace_path(f"observations/ux/work-checkpoints/{request.checkpoint_id}.json", base)
    path.parent.mkdir(parents=True, exist_ok=True)
    with workspace_path(path.with_suffix(".lock"), base).open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if request.action == "create":
            if path.exists():
                raise ValueError("checkpoint already exists; reuse it without resetting attempts")
            state = _create(request, base)
        else:
            state = _Checkpoint.model_validate_json(path.read_text(encoding="utf-8"))
            if state.id != request.checkpoint_id or state.session_id != request.session_id:
                raise ValueError("checkpoint belongs to a different coordinator")
            if state.seal != _digest(state.model_dump(mode="json", exclude={"seal"})):
                raise ValueError("checkpoint integrity unknown")
        gaps = _gaps(state, base)
        delegate = None
        if request.action in {"start", "collect"} and gaps:
            return _result(state, gaps, None)
        if request.action == "start":
            state, step = _start(state, base)
            delegate = _brief(step, state, base) if step else None
        elif request.action in {"collect", "pause"}:
            state = _finish(state, request, base)
        if request.action != "status":
            state = _save(path, state)
        return _result(state, gaps, delegate)
