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
    transport = ""
    if request.target_agent == "bard":
        transport = (
            "Bard is CLI-only and has no MCP server. Resolve its installed plugin root "
            "from BARD_PLUGIN_ROOT, PLUGIN_ROOT, <workspace>/plugins/bard, "
            "$HOME/.agents/plugins/bard, or $HOME/.openhands/plugins/installed/bard "
            "by requiring scripts/bard_cli.py to exist. Invoke the bard_cli.py commands "
            "below as python3 <resolved-plugin-root>/scripts/bard_cli.py with "
            "--root <shared-workspace>; record and ux-respond also require "
            "--json <payload-file|->. If the CLI is absent, report the installed release "
            "as unavailable for liaison; do not invent MCP tools or a response. "
        )
    prompt = (
        f"{transport}Read `{request_path}` with `{sister.inbox_tool}` before acting. "
        "Complete the requested work in the shared workspace and honor its inputs, "
        "acceptance criteria, and dependencies. Record a consequential decision with "
        f"`{sister.record_decision_tool}` and a stage impression with "
        f"`{sister.record_impression_tool}`; cite both returned event IDs in your response. "
        "Answer only through "
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
