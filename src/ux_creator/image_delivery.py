"""Bind advisory reviews to existing tool-return evidence, never to perception."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from . import _vrp
from .render import DerivedImageIdentity, ImageIdentity
from .workspace import workspace_path

_SHA256 = r"^[0-9a-f]{64}$"


class _Observation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    sequence: int = Field(ge=1)
    tool_name: str = Field(min_length=1)
    image_path: str | None
    image_sha256: str = Field(pattern=_SHA256)
    image_identity: ImageIdentity | DerivedImageIdentity | None
    identity_status: Literal["bound", "unknown"]
    delivery_evidence: Literal["inline_bytes"]
    session_id: str | None
    actor: dict[str, JsonValue] | None
    tool_call_id: str | None
    event_id: str = Field(pattern=_SHA256)
    recorded_at: str = Field(min_length=1)


class ImageDelivery(BaseModel):
    """A computed delivery reference; an unknown reference is still useful evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    status: Literal["bound", "unknown"]
    scope: Literal["tool-return"] = "tool-return"
    reason: str | None = None
    observation_event_id: str | None = Field(default=None, pattern=_SHA256)
    image_path: str | None = None
    image_sha256: str | None = Field(default=None, pattern=_SHA256)
    session_id: str | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    producer_identity_status: Literal["bound", "unknown"] = "unknown"
    image_identity: ImageIdentity | DerivedImageIdentity | None = None


def original_review_images(log: Path, image: Path, root: Path) -> list[Path]:
    """Collapse declared auxiliary views to intact original review subjects."""
    rows, malformed = _vrp.load_jsonl(log)
    if malformed:
        raise ValueError("image ancestry unknown: malformed observation log")
    digest = _vrp.sha256_file(image)
    identities: dict[str, DerivedImageIdentity] = {}
    for row in rows:
        claim = row.get("image_identity")
        claim = cast(dict[str, JsonValue], claim) if isinstance(claim, dict) else {}
        if (
            row.get("image_path") != str(image)
            or row.get("image_sha256") != digest
            or claim.get("origin") != "derived"
        ):
            continue
        session = row.get("session_id")
        delivery = review_image_delivery(log, image, digest, str(session) if session else None)
        identity = delivery.image_identity
        if delivery.status != "bound" or not isinstance(identity, DerivedImageIdentity):
            raise ValueError("image ancestry unknown: invalid or ambiguous delivery")
        identities[identity.model_dump_json()] = identity
    if len(identities) > 1:
        raise ValueError("image ancestry unknown: conflicting original revisions")
    if not identities:
        return [image]
    identity = next(iter(identities.values()))
    originals: list[Path] = []
    for parent in identity.parents:
        path = workspace_path(parent.path, root)
        if _vrp.sha256_file(path) != parent.sha256:
            raise ValueError("image ancestry unknown: original revision changed")
        originals.append(path)
    return originals


def review_image_delivery(
    log: Path, image: Path | None, digest: str | None, session_id: str | None
) -> ImageDelivery:
    """Match a reviewer's own delivered path/revision; preserve every uncertainty."""
    if image is None or digest is None:
        return ImageDelivery(status="unknown", reason="missing_image")
    if not session_id:
        return ImageDelivery(status="unknown", reason="missing_native_session")
    try:
        rows, malformed = _vrp.load_jsonl(log)
    except (OSError, UnicodeError):
        return ImageDelivery(status="unknown", reason="unreadable_observation_log")
    except (ValueError, RecursionError):
        return ImageDelivery(status="unknown", reason="invalid_observation_log")
    if malformed:
        return ImageDelivery(status="unknown", reason="invalid_observation_log")
    matched: _Observation | None = None
    sequence = 0
    for row in rows:
        # Historical filename-only observations do not establish delivery.
        if row.get("delivery_evidence") != "inline_bytes":
            continue
        try:
            observation = _Observation.model_validate(row)
        except ValidationError:
            return ImageDelivery(status="unknown", reason="invalid_observation_log")
        content = {
            key: value for key, value in row.items() if key not in {"event_id", "recorded_at"}
        }
        encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if (
            hashlib.sha256(encoded).hexdigest() != observation.event_id
            or observation.sequence <= sequence
        ):
            return ImageDelivery(status="unknown", reason="invalid_observation_log")
        sequence = observation.sequence
        if (
            observation.session_id == session_id
            and observation.image_path == str(image)
            and observation.image_sha256 == digest
        ):
            if matched is not None:
                return ImageDelivery(status="unknown", reason="ambiguous_delivery")
            matched = observation
    if matched is None:
        return ImageDelivery(status="unknown", reason="no_matching_delivery")
    identity = matched.image_identity
    bound = (
        matched.identity_status == "bound"
        and identity is not None
        and identity.path == matched.image_path
        and identity.sha256 == digest
    )
    return ImageDelivery(
        status="bound",
        observation_event_id=matched.event_id,
        image_path=matched.image_path,
        image_sha256=digest,
        session_id=matched.session_id,
        tool_name=matched.tool_name,
        tool_call_id=matched.tool_call_id,
        producer_identity_status="bound" if bound else "unknown",
        image_identity=identity if bound else None,
    )
