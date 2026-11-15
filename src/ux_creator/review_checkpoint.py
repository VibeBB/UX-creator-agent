"""Bound review-record collection; execution and history belong to the SDK."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from . import _vrp
from .image_delivery import ImageDelivery, review_image_delivery
from .workspace import workspace_path, workspace_root

_SHA = r"^[0-9a-f]{64}$"
Role = Literal["primary", "blind", "tiebreak"]


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ReviewSource(_Strict):
    image_path: str = Field(min_length=1)
    checklist: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")


class ReviewCheckpointInput(_Strict):
    action: Literal["create", "status", "start", "collect", "pause", "tiebreak"]
    checkpoint_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    session_id: str = Field(min_length=1)
    contract_path: str | None = None
    sources: list[ReviewSource] = Field(default_factory=list[ReviewSource], max_length=100)
    pair_id: str | None = Field(default=None, pattern=_SHA)
    review_event_id: str | None = Field(default=None, pattern=_SHA)
    reason: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def _arguments(self) -> ReviewCheckpointInput:
        if self.session_id != self.session_id.strip():
            raise ValueError("session_id must not contain surrounding whitespace")
        if self.action == "create":
            if not self.contract_path or not self.sources:
                raise ValueError("create requires contract_path and sources")
        elif self.contract_path is not None or self.sources:
            raise ValueError("only create accepts contract_path and sources")
        if (self.action in {"collect", "tiebreak"}) != (self.pair_id is not None):
            raise ValueError("collect and tiebreak require pair_id; other actions forbid it")
        if (self.action == "collect") != (self.review_event_id is not None):
            raise ValueError("only collect requires review_event_id")
        if (self.action == "pause") != (self.reason is not None):
            raise ValueError("only pause requires a reason")
        return self


class _Artifact(_Strict):
    path: str
    sha256: str = Field(pattern=_SHA)


class _Pair(_Strict):
    id: str = Field(pattern=_SHA)
    image: _Artifact
    checklist: str
    role: Role
    attempts: int = Field(default=0, ge=0, le=2)
    active: bool = False
    after_sequence: int = Field(default=0, ge=0)
    review_event_id: str | None = Field(default=None, pattern=_SHA)
    gap: str | None = None
    attempt_gaps: list[str] = Field(default_factory=list[str], max_length=2)
    reconcile_event_id: str | None = Field(default=None, pattern=_SHA)


class _Checkpoint(_Strict):
    schema_version: Literal[1] = 1
    id: str
    session_id: str
    contract: _Artifact
    pairs: list[_Pair] = Field(min_length=2, max_length=300)
    max_attempts_per_pair: Literal[2] = 2
    seal: str = Field(pattern=_SHA)


class _Review(_Strict):
    event_id: str
    sequence: int
    session_id: str
    image_path: str | None = None
    image_sha256: str | None = None
    checklist: str
    reviewer: Role
    coordinator_session_id: str | None = None
    primary_event_id: str | None = None
    image_delivery: ImageDelivery
    findings: list[dict[str, JsonValue]]


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _artifact(value: str, base: Path) -> _Artifact:
    path = workspace_path(value, base)
    return _Artifact(path=path.relative_to(base).as_posix(), sha256=_vrp.sha256_file(path))


def _new_pair(image: _Artifact, checklist: str, role: Role) -> _Pair:
    return _Pair(
        id=_digest([image.path, image.sha256, checklist, role]),
        image=image,
        checklist=checklist,
        role=role,
    )


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


def _reviews(base: Path) -> dict[str, _Review]:
    rows, problems = _vrp.verify_log(
        workspace_path("observations/ux/vision-reviews.jsonl", base), "vision_review"
    )
    if problems:
        raise ValueError("review evidence unknown: " + problems[0])
    # Event-only records retain their sequence but cannot complete an image pair.
    # Legacy records without native session/delivery cannot complete this collection.
    return {
        str(row["event_id"]): _Review.model_validate(
            {key: row[key] for key in _Review.model_fields if key in row}
        )
        for row in rows
        if row.get("session_id") and row.get("image_delivery") is not None
    }


def _primary(state: _Checkpoint, pair: _Pair) -> _Pair:
    return next(p for p in state.pairs if p.image == pair.image and p.role == "primary")


def _evidence_gap(
    state: _Checkpoint, pair: _Pair, reviews: dict[str, _Review], base: Path
) -> str | None:
    review = reviews.get(pair.review_event_id or "")
    if review is None:
        return "missing_review_evidence"
    if (
        not review.image_path
        or review.sequence <= pair.after_sequence
        or review.image_sha256 != pair.image.sha256
        or review.checklist != pair.checklist
        or review.reviewer != pair.role
        or review.session_id == state.session_id
    ):
        return "review_scope_mismatch"
    try:
        image = workspace_path(review.image_path, base)
    except (OSError, ValueError):
        return "unavailable_review_path"
    if image != base / pair.image.path:
        return "review_scope_mismatch"
    primary = _primary(state, pair)
    if pair.role == "primary":
        if review.coordinator_session_id != state.session_id or review.primary_event_id:
            return "coordinator_mismatch"
    elif (
        not primary.review_event_id
        or review.primary_event_id != primary.review_event_id
        or primary.review_event_id not in reviews
        or review.session_id == reviews[primary.review_event_id].session_id
    ):
        return "independent_review_mismatch"
    if any(
        p.id != pair.id
        and p.image == pair.image
        and p.review_event_id in reviews
        and reviews[p.review_event_id].session_id == review.session_id
        for p in state.pairs
        if p.review_event_id
    ):
        return "reused_reviewer_session"
    override = os.environ.get("UX_IMAGE_OBSERVATIONS")
    log = (
        Path(override).expanduser()
        if override
        else Path("observations/ux/image-observations.jsonl")
    )
    delivery = review_image_delivery(
        log if log.is_absolute() else workspace_path(log, base),
        base / pair.image.path,
        pair.image.sha256,
        review.session_id,
    )
    if delivery.status != "bound" or review.image_delivery != delivery:
        return "unverified_image_delivery"
    return None


def _gaps(state: _Checkpoint, reviews: dict[str, _Review], base: Path) -> list[str]:
    gaps: list[str] = []
    for artifact in [state.contract, *(p.image for p in state.pairs)]:
        try:
            if _artifact(artifact.path, base) != artifact:
                gaps.append("changed_input:" + artifact.path)
        except (OSError, ValueError):
            gaps.append("unavailable_input:" + artifact.path)
    for pair in state.pairs:
        if pair.review_event_id and (gap := _evidence_gap(state, pair, reviews, base)):
            gaps.append(f"{gap}:{pair.id}")
        if pair.role == "tiebreak" and pair.reconcile_event_id not in _round_one(
            state, pair, base, reviews
        ):
            gaps.append(f"unverified_round1_reconcile:{pair.id}")
    return sorted(set(gaps))


def _eligible(state: _Checkpoint) -> list[_Pair]:
    return [
        p
        for p in state.pairs
        if not p.review_event_id
        and not p.active
        and p.attempts < state.max_attempts_per_pair
        and (p.role == "primary" or _primary(state, p).review_event_id)
    ]


def _recover(state: _Checkpoint, reviews: dict[str, _Review], base: Path) -> _Checkpoint:
    """Collect intact records left by stopped children before spending another attempt."""
    for pair in state.pairs:
        if pair.review_event_id or pair.attempts == 0:
            continue
        candidates: list[_Pair] = []
        for event_id in reviews:
            candidate = pair.model_copy(update={"review_event_id": event_id})
            if not _evidence_gap(state, candidate, reviews, base):
                candidates.append(candidate)
        if len(candidates) > 1:
            raise ValueError("ambiguous uncollected review evidence: " + pair.id)
        if candidates:
            recovered = candidates[0].model_copy(update={"gap": None})
            state = state.model_copy(
                update={"pairs": [recovered if p == pair else p for p in state.pairs]}
            )
    return state


def _brief(state: _Checkpoint, pair: _Pair) -> dict[str, str]:
    # Never include checkpoint paths, previous prose or the previous child's history.
    scope = (
        f"coordinator_session_id={state.session_id}"
        if pair.role == "primary"
        else f"primary_event_id={_primary(state, pair).review_event_id}"
    )
    return {
        "subagent_type": "ux-review" if pair.role == "primary" else "ux-blind-review",
        "description": f"UX {pair.role} image review",
        "prompt": (
            f"Review exactly one image: {json.dumps(pair.image.path)} "
            f"(SHA-256 {pair.image.sha256}); contract {json.dumps(state.contract.path)} "
            f"(SHA-256 {state.contract.sha256}); checklist={pair.checklist}; "
            f"reviewer={pair.role}; {scope}. Use your own SessionStart native session_id. "
            "Inspect the inline image and write ux_record_vision_review, including the "
            "scope fields above. If inspection is unavailable, report unknown. Return "
            "only the event ID or an explicit gap. Do not read earlier reviews."
        ),
    }


def _round_one(
    state: _Checkpoint, pair: _Pair, base: Path, reviews: dict[str, _Review]
) -> set[str]:
    siblings = [p for p in state.pairs if p.image == pair.image and p.role != "tiebreak"]
    if len(siblings) != 2 or any(p.review_event_id not in reviews for p in siblings):
        return set()
    primary, blind = [reviews[p.review_event_id or ""].model_dump() for p in siblings]
    expected = _vrp.reconcile(primary, [blind])
    rows, problems = _vrp.verify_log(
        workspace_path("observations/ux/reconciles.jsonl", base), "review_reconcile"
    )
    if problems:
        raise ValueError("reconcile evidence unknown: " + problems[0])
    return {
        str(r["event_id"])
        for r in rows
        if r.get("reviews") == [p.review_event_id for p in siblings]
        and r.get("outcome") == "disagree"
        and r.get("round") == 1
        and r.get("image_sha256") == pair.image.sha256
        and expected["outcome"] == "disagree"
        and r.get("metrics") == expected["metrics"]
        and r.get("session_id") == state.session_id
    }


def _tiebreak(
    state: _Checkpoint, pair_id: str, base: Path, reviews: dict[str, _Review]
) -> _Checkpoint:
    pair = next((p for p in state.pairs if p.id == pair_id), None)
    if pair is None:
        raise ValueError("unknown pair_id")
    siblings = [p for p in state.pairs if p.image == pair.image]
    if len(siblings) != 2 or any(not p.review_event_id for p in siblings):
        raise ValueError("tiebreak needs completed primary/blind and is allowed only once")
    reconciles = _round_one(state, pair, base, reviews)
    if not reconciles:
        raise ValueError("tiebreak needs an intact coordinator round-1 disagreement")
    tiebreak = _new_pair(pair.image, pair.checklist, "tiebreak").model_copy(
        update={"reconcile_event_id": sorted(reconciles)[0]}
    )
    return state.model_copy(update={"pairs": [*state.pairs, tiebreak]})


def review_checkpoint(
    payload: dict[str, JsonValue], root: Path | None = None
) -> dict[str, JsonValue]:
    """Issue fresh-task briefs and retain evidence references, never execute children."""
    request = ReviewCheckpointInput.model_validate(payload)
    native = os.environ.get("OPENHANDS_SESSION_ID")
    if native and native != request.session_id:
        raise ValueError("session_id does not match OPENHANDS_SESSION_ID")
    base = (root or workspace_root()).resolve()
    path = workspace_path(f"observations/ux/review-checkpoints/{request.checkpoint_id}.json", base)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = workspace_path(path.with_suffix(".lock"), base)
    with lock_path.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if request.action == "create":
            if path.exists():
                raise ValueError("checkpoint already exists; use status/start without resetting it")
            pairs = [
                _new_pair(_artifact(s.image_path, base), s.checklist, role)
                for s in request.sources
                for role in ("primary", "blind")
            ]
            if len({p.image.path for p in pairs}) != len(request.sources):
                raise ValueError("sources must have unique resolved image paths")
            state = _Checkpoint(
                id=request.checkpoint_id,
                session_id=request.session_id,
                contract=_artifact(request.contract_path or "", base),
                pairs=pairs,
                seal="0" * 64,
            )
        else:
            state = _Checkpoint.model_validate_json(path.read_text(encoding="utf-8"))
            if state.id != request.checkpoint_id or state.session_id != request.session_id:
                raise ValueError("checkpoint belongs to a different coordinator")
            if state.seal != _digest(state.model_dump(mode="json", exclude={"seal"})):
                raise ValueError("checkpoint integrity unknown")
        reviews = _reviews(base)
        gaps = _gaps(state, reviews, base)
        brief: dict[str, str] | None = None
        active = next((p for p in state.pairs if p.active), None)
        if request.action in {"start", "collect", "tiebreak"} and gaps:
            raise ValueError("checkpoint blocked: " + "; ".join(gaps))
        if request.action == "start":
            if active:
                raise ValueError("no eligible pair: active child")
            recovered = _recover(state, reviews, base)
            eligible = _eligible(recovered)
            if not eligible and recovered == state:
                raise ValueError("no eligible pair: exhausted attempts or collected")
            state = recovered
            if eligible:
                pair = eligible[0]
                active = pair.model_copy(
                    update={
                        "active": True,
                        "attempts": pair.attempts + 1,
                        # Preserve the first reservation for interrupted-record recovery.
                        "after_sequence": (
                            pair.after_sequence
                            if pair.attempts
                            else max((r.sequence for r in reviews.values()), default=0)
                        ),
                        "gap": None,
                    }
                )
                state = state.model_copy(
                    update={"pairs": [active if p == pair else p for p in state.pairs]}
                )
                brief = _brief(state, active)
        elif request.action in {"collect", "pause"}:
            if active is None or (request.action == "collect" and request.pair_id != active.id):
                raise ValueError("operation requires the active pair")
            updated = active.model_copy(
                update={
                    "active": False,
                    "gap": request.reason,
                    "review_event_id": request.review_event_id,
                    "attempt_gaps": (
                        [*active.attempt_gaps, request.reason]
                        if request.reason is not None
                        else active.attempt_gaps
                    ),
                }
            )
            if request.action == "collect" and (
                gap := _evidence_gap(state, updated, reviews, base)
            ):
                raise ValueError("review evidence unknown: " + gap)
            state = state.model_copy(
                update={"pairs": [updated if p == active else p for p in state.pairs]}
            )
        elif request.action == "tiebreak":
            if active:
                raise ValueError("wait for the active child before requesting a tiebreak")
            state = _tiebreak(state, request.pair_id or "", base, reviews)
        if request.action != "status":
            state = _save(path, state)
        pending = [p for p in state.pairs if not p.review_event_id]
        status = (
            "blocked"
            if gaps
            else "running"
            if any(p.active for p in state.pairs)
            else "collected"
            if not pending
            else "paused"
            if _eligible(state)
            else "blocked"
        )
        return cast(
            dict[str, JsonValue],
            {
                "verdict": "ok",
                "scope": "review-record-collection",
                "status": status,
                "checkpoint": path.relative_to(base).as_posix(),
                "acceptance": "unknown",
                "gaps": gaps + [f"{p.id}:{p.gap or 'review_missing'}" for p in pending],
                "pairs": [p.model_dump(mode="json") for p in state.pairs],
                "delegate": brief,
            },
        )
