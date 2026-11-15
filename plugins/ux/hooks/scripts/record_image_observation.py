"""Record inline image delivery, producer claims and native observer identity.

Only bytes present in the tool response establish delivery. A filename in
text is insufficient; the filesystem may already contain a newer revision.
Producer claims are advisory and never supply a gate verdict.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

EVENTS_ENV = "UX_IMAGE_OBSERVATIONS"
EVENTS_RELATIVE_PATH = Path("observations/ux/image-observations.jsonl")
MCP_TOOLS = {"ux_render", "ux_author", "ux_produce", "ux_liaison_status"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
_IMAGE_MIMES = {"image/png", "image/jpeg"}
_OWNERS = {
    "ux",
    "bard",
    "circuit",
    "dashboard",
    "doc",
    "firmware",
    "fpga",
    "mech",
    "prodeng",
    "sim",
    "wire",
}
_ACTOR_KEYS = {
    "agent",
    "agent_name",
    "actor",
    "subagent_type",
    "task_agent",
    "action_id",
    "tool_call_id",
    "parent_id",
    "call_id",
}


def _mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _items(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []


def _tool_name(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    if value == "file_editor" or value in MCP_TOOLS:
        return value
    # SDK multi-server configurations use {server_name}_{tool_name}.
    name = value.removeprefix("ux_")
    return name if name in MCP_TOOLS else None


def _project_dir(payload: dict[str, object]) -> Path:
    working_dir = payload.get("working_dir")
    fallback = working_dir if isinstance(working_dir, str) else "."
    return Path(os.environ.get("OPENHANDS_PROJECT_DIR") or fallback).resolve()


def _events_path(base: Path) -> Path:
    override = os.environ.get(EVENTS_ENV)
    path = Path(override).expanduser() if override else EVENTS_RELATIVE_PATH
    return path if path.is_absolute() else base / path


def _digest(encoded: str) -> str | None:
    try:
        return hashlib.sha256(base64.b64decode(encoded, validate=True)).hexdigest()
    except (binascii.Error, ValueError):
        return None


def _image_digests(response: dict[str, object]) -> Counter[str]:
    digests: Counter[str] = Counter()
    for value in _items(response.get("content")):
        block = _mapping(value)
        if block.get("type") != "image":
            continue
        data = block.get("data")
        mime = block.get("mimeType", block.get("mime_type"))
        if isinstance(data, str) and isinstance(mime, str) and mime in _IMAGE_MIMES:
            digest = _digest(data)
            if digest is not None:
                digests[digest] += 1
            continue
        # OpenHands converts MCP blocks into ImageContent.image_urls.
        for url in _items(block.get("image_urls")):
            if not isinstance(url, str):
                continue
            header, separator, encoded = url.partition(",")
            if not separator or header not in {f"data:{mime};base64" for mime in _IMAGE_MIMES}:
                continue
            digest = _digest(encoded)
            if digest is not None:
                digests[digest] += 1
    return digests


def _inline_metadata(response: dict[str, object]) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for value in _items(response.get("content")):
        block = _mapping(value)
        text = block.get("text")
        if block.get("type") != "text" or not isinstance(text, str):
            continue
        try:
            payload = _mapping(json.loads(text))
        except json.JSONDecodeError:
            continue
        if "inline_images" in payload:
            payloads.append(payload)
    if len(payloads) != 1:
        return []
    return [_mapping(item) for item in _items(payloads[0].get("inline_images"))]


def _image_path(candidate: object, base: Path) -> Path | None:
    if not isinstance(candidate, str) or not candidate:
        return None
    path = Path(candidate)
    if path.suffix.lower() not in _IMAGE_SUFFIXES:
        return None
    try:
        return (base / path).resolve()
    except (OSError, ValueError):
        return None


def _producer_claim(
    metadata: dict[str, object], path: Path, digest: str
) -> dict[str, object] | None:
    claim = _mapping(metadata.get("image_identity"))
    owner, origin, source = claim.get("owner_plugin"), claim.get("origin"), claim.get("path")
    if (
        metadata.get("identity_status") != "bound"
        or set(claim) != {"path", "sha256", "owner_plugin", "origin"}
        or claim.get("sha256") != digest
        or not isinstance(owner, str)
        or owner not in _OWNERS
        or origin not in ("renderer", "liaison-response")
        or not isinstance(source, str)
        or not Path(source).is_absolute()
        or str(path) != source
    ):
        return None
    return claim


def _observation(
    path: Path | None, digest: str, claim: dict[str, object] | None = None
) -> dict[str, object]:
    return {
        "image_path": str(path) if path is not None else None,
        "image_sha256": digest,
        "image_identity": claim,
        "identity_status": "bound" if claim is not None else "unknown",
        "delivery_evidence": "inline_bytes",
    }


def _observations(payload: dict[str, object], tool: str, base: Path) -> list[dict[str, object]]:
    response = _mapping(payload.get("tool_response"))
    if "error" in response or response.get("is_error") or response.get("isError"):
        return []
    digests = _image_digests(response)
    if tool == "file_editor":
        action = _mapping(payload.get("tool_input"))
        if action.get("command") != "view":
            return []
        path = _image_path(action.get("path"), base)
        if path is not None and digests.total() == 1:
            return [_observation(path, next(iter(digests)))]
    observations: list[dict[str, object]] = []
    if tool != "file_editor":
        for metadata in _inline_metadata(response):
            digest = metadata.get("sha256")
            path = _image_path(metadata.get("path"), base)
            if (
                metadata.get("attached") is not True
                or metadata.get("identity_status") == "mismatch"
                or path is None
                or not isinstance(digest, str)
                or digests[digest] < 1
            ):
                continue
            claim = _producer_claim(metadata, path, digest)
            observations.append(_observation(path, digest, claim))
            digests[digest] -= 1
    # Unassociated bytes remain an explicit gap, never a guessed filename.
    observations.extend(_observation(None, digest) for digest in digests.elements())
    return observations


def main() -> int:
    try:
        payload = _mapping(json.load(sys.stdin))
        tool = _tool_name(payload.get("tool_name"))
        if tool is None:
            return 0
        base = _project_dir(payload)
        observations = _observations(payload, tool, base)
        if not observations:
            return 0
        path = _events_path(base)
        path.parent.mkdir(parents=True, exist_ok=True)
        sequence = 1
        if path.exists():
            sequence += len(path.read_text(encoding="utf-8").splitlines())
        with path.open("a", encoding="utf-8") as stream:
            for observation in observations:
                record = {
                    "sequence": sequence,
                    "tool_name": payload["tool_name"],
                    **observation,
                    "session_id": payload.get("session_id"),
                    "actor": {key: payload[key] for key in sorted(payload) if key in _ACTOR_KEYS}
                    or None,
                    "tool_call_id": payload.get("tool_call_id") or payload.get("action_id"),
                }
                encoded = json.dumps(record, sort_keys=True, separators=(",", ":"))
                record["event_id"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
                record["recorded_at"] = datetime.now(UTC).isoformat()
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                sequence += 1
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        print(f"image observation log unavailable: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
