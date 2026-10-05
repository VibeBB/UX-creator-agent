"""Deterministic task-tool briefs for sister-agent UX requests."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

from .requests import UXRequest
from .sisters import SISTERS


def delegation_brief(request: UXRequest, liaison_dir_rel: str) -> dict[str, str]:
    path = PurePosixPath(liaison_dir_rel)
    if (
        not liaison_dir_rel.strip()
        or "\\" in liaison_dir_rel
        or path.is_absolute()
        or PureWindowsPath(liaison_dir_rel).is_absolute()
        or ".." in path.parts
    ):
        raise ValueError("liaison_dir_rel must be a workspace-relative directory")
    sister = SISTERS[request.target_agent]
    request_path = f"{path.as_posix()}/{request.id}.ux-request.json"
    prompt = (
        f"Read `{request_path}` with `{sister.inbox_tool}` before acting. "
        "Complete the requested work in the shared workspace and honor its inputs, "
        "acceptance criteria, and dependencies. Record a consequential decision with "
        "`ux_record_decision` and a stage impression with `ux_record_impression`; cite "
        "both returned event IDs in your response. Answer only through "
        f"`{sister.respond_tool}`, including input hashes, artifact paths and hashes, "
        "gate verdicts, decision_refs, impression_refs, and any questions_for_user. "
        "Never hand-write or edit the response JSON. If your agent is unavailable, "
        f"leave `{request_path}` unchanged and tell the user to open it in the "
        f"`{sister.repo}` plugin; do not fabricate a response."
    )
    return {
        "subagent_type": sister.liaison_agent,
        "description": f"{request.target_agent} answer {request.id}",
        "prompt": prompt,
    }
