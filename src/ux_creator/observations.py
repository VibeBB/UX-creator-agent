"""Read-only summaries of VRP records across the VibeBB plugin family."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, cast

from .records import tree_sha256
from .sisters import SHA256, TARGET_AGENTS
from .workspace import workspace_path

_RECORD_FILES: Final = {
    "decisions": "decisions.jsonl",
    "impressions": "impressions.jsonl",
    "vision_reviews": "vision-reviews.jsonl",
}
_PLUGINS: Final = ("ux", *TARGET_AGENTS)


@dataclass(frozen=True)
class PluginRecords:
    plugin: str
    present: bool
    counts: dict[str, int]
    malformed_line_count: int
    latest_decisions: list[dict[str, object]]
    latest_impressions: list[dict[str, object]]
    latest_vision_reviews: list[dict[str, object]]
    last_stop_verdict: str | None


def _read_jsonl(path: Path, workspace: Path) -> tuple[list[dict[str, object]], int]:
    try:
        path = workspace_path(path, workspace)
    except (OSError, ValueError):
        return [], 1
    if not path.is_file():
        return [], 0
    records: list[dict[str, object]] = []
    malformed = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return [], 1
    for line in lines:
        try:
            value: object = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        if not isinstance(value, dict):
            malformed += 1
            continue
        record = cast(dict[str, object], value)
        event_id = record.get("event_id")
        if not isinstance(event_id, str) or not SHA256.fullmatch(event_id):
            malformed += 1
            continue
        records.append(record)
    return records, malformed


def _field(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    return value if isinstance(value, str) else ""


def _latest(records: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        records,
        key=lambda item: (_field(item, "recorded_at"), _field(item, "event_id")),
        reverse=True,
    )[:5]


def _fresh_artifacts(artifacts: object, workspace: Path) -> bool:
    if not isinstance(artifacts, list):
        return False
    for artifact in cast(list[object], artifacts):
        if not isinstance(artifact, dict):
            return False
        artifact_record = cast(dict[str, object], artifact)
        path_value = artifact_record.get("path")
        digest = artifact_record.get("sha256")
        if not isinstance(path_value, str) or not isinstance(digest, str):
            return False
        try:
            path = workspace_path(path_value, workspace)
            if not path.exists() or tree_sha256(path) != digest:
                return False
        except (OSError, ValueError):
            return False
    return True


def _decisions(records: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "event_id": record.get("event_id"),
            "id": record.get("id"),
            "stage": record.get("stage"),
            "question": record.get("question"),
            "chosen": record.get("chosen"),
            "decided_by": record.get("decided_by"),
            "recorded_at": record.get("recorded_at"),
        }
        for record in _latest(records)
    ]


def _impressions(records: list[dict[str, object]], workspace: Path) -> list[dict[str, object]]:
    return [
        {
            "event_id": record.get("event_id"),
            "stage": record.get("stage"),
            "artifacts": record.get("artifacts", []),
            "fresh": _fresh_artifacts(record.get("artifacts", []), workspace),
            "excerpt": _field(record, "impression")[:200],
            "recorded_at": record.get("recorded_at"),
        }
        for record in _latest(records)
    ]


def _vision_reviews(records: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for record in _latest(records):
        findings = record.get("findings")
        counts = {"info": 0, "warning": 0, "error": 0}
        if isinstance(findings, list):
            for finding in cast(list[object], findings):
                if isinstance(finding, dict):
                    severity = cast(dict[str, object], finding).get("severity")
                    if isinstance(severity, str) and severity in counts:
                        counts[severity] += 1
        result.append(
            {
                "event_id": record.get("event_id"),
                "checklist": record.get("checklist"),
                "image_path": record.get("image_path"),
                "findings_by_severity": counts,
                "excerpt": _field(record, "impression")[:200],
                "recorded_at": record.get("recorded_at"),
            }
        )
    return result


def _stop_verdict(directory: Path, workspace: Path) -> str | None:
    try:
        path = workspace_path(directory / "records-status.json", workspace)
    except (OSError, ValueError):
        return "unknown"
    if not path.is_file():
        return None
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "unknown"
    if isinstance(payload, dict):
        verdict = cast(dict[str, object], payload).get("verdict")
        if isinstance(verdict, str):
            return verdict
    return "unknown"


def collect_records(workspace: Path) -> dict[str, PluginRecords]:
    """Summarize each plugin's latest records without mutating the workspace."""
    result: dict[str, PluginRecords] = {}
    for plugin in _PLUGINS:
        directory = workspace / "observations" / plugin
        present = False
        try:
            directory = workspace_path(directory, workspace)
            present = directory.is_dir()
        except (OSError, ValueError):
            pass
        loaded = {
            kind: _read_jsonl(directory / filename, workspace)
            for kind, filename in _RECORD_FILES.items()
        }
        records = {kind: pair[0] for kind, pair in loaded.items()}
        malformed = sum(pair[1] for pair in loaded.values())
        result[plugin] = PluginRecords(
            plugin=plugin,
            present=present,
            counts={kind: len(rows) for kind, rows in records.items()},
            malformed_line_count=malformed,
            latest_decisions=_decisions(records["decisions"]),
            latest_impressions=_impressions(records["impressions"], workspace),
            latest_vision_reviews=_vision_reviews(records["vision_reviews"]),
            last_stop_verdict=_stop_verdict(directory, workspace),
        )
    return result


def records_to_dict(records: dict[str, PluginRecords]) -> dict[str, dict[str, object]]:
    return {plugin: asdict(summary) for plugin, summary in records.items()}
