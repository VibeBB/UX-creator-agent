"""Sister-agent responses — close the ux-request loop.

A sister answers `<stem>.ux-request.json` by writing
`<stem>.ux-response.json` beside it. `liaison_status` reconciles the
requests a directory contains against the responses beside them: each
request is `open`, `answered`, or `mismatched` (a response from the
wrong responder). Everything here is informational — a rejected or
unanswered request is a design signal for the persona, never a gate
input (ADR-0008).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .requests import TARGET_AGENTS, UXRequest

ResponseStatus = Literal["accepted", "rejected", "deferred", "needs_info"]


class UXResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    system: Literal["ux-creator"] = "ux-creator"
    request: str = Field(min_length=1)
    responder: str = Field(min_length=1)
    status: ResponseStatus
    reason: str = ""
    artifacts: list[str] = Field(default_factory=list[str])


class LiaisonEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: str
    target_agent: str
    risk: Literal["low", "high"]
    state: Literal["open", "answered", "mismatched"]
    response_status: ResponseStatus | None = None
    reason: str = ""
    response_path: str = ""


class LiaisonStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[LiaisonEntry]
    orphans: list[str]
    malformed: list[str]


def _normalise_request_ref(ref: str) -> str:
    stem = ref
    for suffix in (".ux-request.json", ".json"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return stem


def load_responses(
    dir: Path,
) -> tuple[list[tuple[Path, UXResponse]], list[Path]]:
    """Parse every *.ux-response.json under dir.

    Returns (valid records, malformed paths). Malformed files are listed,
    never raised. Unknown responders are malformed (fail-closed).
    """
    ok: list[tuple[Path, UXResponse]] = []
    malformed: list[Path] = []
    for path in sorted(dir.glob("*.ux-response.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            response = UXResponse.model_validate(payload)
            if response.responder not in TARGET_AGENTS:
                raise ValueError(
                    f"unknown responder {response.responder!r}; expected one of {TARGET_AGENTS}"
                )
        except (OSError, ValueError):
            malformed.append(path)
            continue
        ok.append((path, response))
    return ok, malformed


def _load_requests(
    dir: Path,
) -> tuple[list[tuple[str, UXRequest]], list[Path]]:
    ok: list[tuple[str, UXRequest]] = []
    malformed: list[Path] = []
    for path in sorted(dir.glob("*.ux-request.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            request = UXRequest.model_validate(payload)
        except (OSError, ValueError):
            malformed.append(path)
            continue
        ok.append((path.stem.removesuffix(".ux-request"), request))
    return ok, malformed


def liaison_status(requests_dir: Path, responses_dir: Path) -> LiaisonStatus:
    requests, malformed_req = _load_requests(requests_dir)
    responses, malformed_resp = load_responses(responses_dir)

    latest: dict[str, tuple[Path, UXResponse]] = {}
    for path, response in responses:  # sorted paths: later wins
        latest[_normalise_request_ref(response.request)] = (path, response)

    entries: list[LiaisonEntry] = []
    orphans: list[str] = []
    seen = {stem for stem, _r in requests}
    for stem, request in requests:
        hit = latest.get(stem)
        if hit is None:
            entries.append(
                LiaisonEntry(
                    request=stem, target_agent=request.target_agent, risk=request.risk, state="open"
                )
            )
            continue
        path, response = hit
        state: Literal["answered", "mismatched"] = (
            "answered" if response.responder == request.target_agent else "mismatched"
        )
        entries.append(
            LiaisonEntry(
                request=stem,
                target_agent=request.target_agent,
                risk=request.risk,
                state=state,
                response_status=response.status,
                reason=response.reason,
                response_path=str(path),
            )
        )
    for stem, (path, _r) in latest.items():
        if stem not in seen:
            orphans.append(str(path))
    entries.sort(key=lambda e: e.request)
    return LiaisonStatus(
        entries=entries,
        orphans=sorted(orphans),
        malformed=sorted(str(p) for p in malformed_req + malformed_resp),
    )
