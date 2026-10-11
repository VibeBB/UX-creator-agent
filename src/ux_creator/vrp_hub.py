"""Family-wide impression aggregation and concern-cycle detection for UX.

UX is the hub of the sister family, so it is the one plugin that reads every
VRP log at once. The view is advisory: it never changes a gate verdict.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path
from typing import Any

from . import _vrp
from .sisters import TARGET_AGENTS
from .workspace import workspace_root

SEVERITIES = ("error", "warning", "info")


def _edges(digest: dict[str, Any]) -> dict[tuple[str, str], list[str]]:
    """Directed "raiser -> owner" edges of every open concern and dispute."""
    edges: dict[tuple[str, str], list[str]] = defaultdict(list)
    for concern in digest.get("open_concerns", []):
        raiser, owner = str(concern.get("system")), str(concern.get("about"))
        if owner and owner != raiser and owner != "None":
            edges[(raiser, owner)].append(f"concern {concern.get('ref', '')}".strip())
    for dispute in digest.get("disputes", []):
        raiser = str(dispute.get("system"))
        owner = str(dispute.get("target", "")).split(":", 1)[0]
        if owner and owner != raiser:
            edges[(raiser, owner)].append(f"dispute {dispute.get('target', '')}".strip())
    return edges


def concern_cycles(digest: dict[str, Any]) -> list[dict[str, Any]]:
    """Elementary cycles in the raiser -> owner graph, smallest node first.

    A cycle means sisters keep handing the same worry around (A worries about
    B, B about C, C back about A) and no single owner can close it alone.
    """
    edges = _edges(digest)
    graph: dict[str, set[str]] = defaultdict(set)
    for raiser, owner in edges:
        graph[raiser].add(owner)
    cycles: list[list[str]] = []
    nodes = sorted(set(graph) | {o for targets in graph.values() for o in targets})
    for start in nodes:
        stack: list[tuple[str, list[str]]] = [(start, [start])]
        while stack:
            node, path = stack.pop()
            for nxt in sorted(graph.get(node, ())):
                if nxt == start:
                    cycles.append(path)
                elif nxt > start and nxt not in path:
                    stack.append((nxt, [*path, nxt]))
    result: list[dict[str, Any]] = []
    for path in sorted(cycles, key=lambda p: (len(p), p)):
        ring = [*path, path[0]]
        result.append(
            {
                "systems": path,
                "evidence": [
                    {"from": a, "to": b, "refs": sorted(edges[(a, b)])} for a, b in pairwise(ring)
                ],
            }
        )
    return result


def aggregate(digest: dict[str, Any]) -> dict[str, Any]:
    """Per-sister counts of what the family thinks, in one table."""
    rows: dict[str, dict[str, Any]] = {}

    def row(system: str) -> dict[str, Any]:
        return rows.setdefault(
            system,
            {
                "concerns_raised": Counter[str](),
                "concerns_owned": Counter[str](),
                "disputes_raised": 0,
                "unanswered_reads": 0,
                "open_insights": 0,
                "review_splits": 0,
            },
        )

    for system in digest.get("systems", {}):
        row(str(system))
    for concern in digest.get("open_concerns", []):
        severity = str(concern.get("severity", "info"))
        row(str(concern.get("system")))["concerns_raised"][severity] += 1
        owner = concern.get("about")
        if owner:
            row(str(owner))["concerns_owned"][severity] += 1
    for dispute in digest.get("disputes", []):
        row(str(dispute.get("system")))["disputes_raised"] += 1
    for read in digest.get("unacknowledged_reads", []):
        row(str(read.get("reader")))["unanswered_reads"] += 1
    for insight in digest.get("insights", []):
        status = insight.get("status")
        if status in (None, "proposed", "tried", "deferred"):
            target = insight.get("target") or str(insight.get("ref", "")).split(":", 1)[0]
            row(str(target))["open_insights"] += 1
    for split in digest.get("review_disagreements", []):
        row(str(split.get("system")))["review_splits"] += 1
    table: dict[str, Any] = {}
    for system in sorted(rows):
        data = rows[system]
        table[system] = {
            **data,
            "concerns_raised": {s: data["concerns_raised"][s] for s in SEVERITIES},
            "concerns_owned": {s: data["concerns_owned"][s] for s in SEVERITIES},
        }
    return table


def hub(root: Path | None = None) -> dict[str, Any]:
    """Aggregate every sister's impressions and flag concern cycles."""
    digest = _vrp.digest(root or workspace_root())
    systems: dict[str, dict[str, Any]] = digest.get("systems", {})
    broken = sorted(system for system, info in systems.items() if info.get("integrity") != "ok")
    cycles = concern_cycles(digest)
    attention = bool(cycles or broken)
    return {
        "schema_version": _vrp.SCHEMA_VERSION,
        "status": "attention" if attention else "clear",
        "advisory": True,
        "broken_logs": broken,
        "cycles": cycles,
        "systems": aggregate(digest),
        "undelivered_songs": [s for s in digest.get("songs", []) if not s.get("received")],
    }


def error_concerns(digest: dict[str, Any]) -> list[dict[str, Any]]:
    """Unresolved (open, deferred or disputed) error-severity concerns."""
    return [c for c in digest.get("open_concerns", []) if c.get("severity") == "error"]


def _upstream(concern: dict[str, Any]) -> dict[str, str]:
    event = str(concern.get("ref", "")).split(":", 1)[-1].split("#", 1)[0]
    return {"system": str(concern.get("system")), "event_id": event}


def escalate(root: Path | None = None) -> dict[str, Any]:
    """Draft the next SLP requests and ECR candidates from unresolved error concerns.

    A concern owned by a sister becomes a ``requested_changes`` line of a draft
    request to that sister; any other owner (UX itself, the user) becomes an
    ECR candidate. Each draft carries the concerns' event ids as ``upstream``
    so the UX decision that acts on it cites where it came from. Advisory:
    nothing is written and no verdict changes.
    """
    digest = _vrp.digest(root or workspace_root())
    requests: dict[str, dict[str, Any]] = {}
    ecr: list[dict[str, Any]] = []
    for concern in error_concerns(digest):
        ref = str(concern.get("ref", ""))
        change = f"{concern.get('text') or 'unresolved concern'} ({ref})"
        owner = str(concern.get("about") or "")
        if owner in TARGET_AGENTS:
            draft = requests.setdefault(
                owner, {"target": owner, "requested_changes": [], "upstream": []}
            )
            draft["requested_changes"].append(change)
            draft["upstream"].append(_upstream(concern))
        else:
            ecr.append(
                {
                    "about": owner,
                    "change": change,
                    "status": concern.get("status"),
                    "upstream": [_upstream(concern)],
                }
            )
    systems: dict[str, dict[str, Any]] = digest.get("systems", {})
    broken = sorted(s for s, info in systems.items() if info.get("integrity") != "ok")
    return {
        "schema_version": _vrp.SCHEMA_VERSION,
        "advisory": True,
        "status": "attention" if requests or ecr or broken else "clear",
        "broken_logs": broken,
        "requests": [requests[target] for target in sorted(requests)],
        "ecr_candidates": ecr,
    }
