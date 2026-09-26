"""Sibling-contract import adapters (ADR-0003).

Sibling artifacts are validated shallowly, their touchpoint candidates
(connector/button/LED/port ids, envelope anchors) are extracted, and a
provenance record `{system, path, sha256, extracted}` is appended to
`contract.imports`. ux-creator never imports sibling code and never links
back: the copy is the truth, re-import produces a new record.

Supported `system` tags: circuit, mech, wire, bard, csv.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

from .contract import ImportRef, UXContract


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not load import source {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"import source {path} is not a JSON object")
    return cast(dict[str, Any], value)


def _objects(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw = data.get(key, [])
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in cast(list[object], raw):
        if isinstance(item, dict):
            out.append(cast(dict[str, Any], item))
    return out


def extract_touchpoints(system: str, data: dict[str, Any]) -> list[str]:
    """Touchpoint candidate ids extracted per sibling contract shape."""
    found: list[str] = []
    if system == "circuit":
        for connector in _objects(data, "connectors"):
            ref = connector.get("ref")
            if isinstance(ref, str) and ref:
                found.append(ref)
                housing = connector.get("housing")
                if isinstance(housing, str) and housing:
                    found.append(housing)
    elif system == "mech":
        for anchor in _objects(data, "anchors"):
            name = anchor.get("name")
            if isinstance(name, str) and name:
                found.append(name)
    elif system == "wire":
        for item in _objects(data, "connectors"):
            ref = item.get("id") or item.get("ref")
            if isinstance(ref, str) and ref:
                found.append(ref)
    elif system == "bard":
        for key in ("artifacts", "outputs"):
            raw = data.get(key, [])
            if isinstance(raw, list):
                found.extend(i for i in cast(list[object], raw) if isinstance(i, str))
    else:  # csv and unknown systems: best-effort id/ref/name scan
        for value in data.values():
            if isinstance(value, list):
                for item in _objects({"_": value}, "_"):
                    for k in ("id", "ref", "name"):
                        candidate = item.get(k)
                        if isinstance(candidate, str) and candidate:
                            found.append(candidate)
                            break
    return sorted(dict.fromkeys(found))


def import_source(contract: UXContract, system: str, path: Path) -> UXContract:
    """Validate a sibling artifact and append its provenance to the contract."""
    data = _load(path)
    declared_system = data.get("system")
    if isinstance(declared_system, str) and declared_system != system:
        raise ValueError(
            f"import source {path} declares system {declared_system!r}, not {system!r}"
        )
    extracted = extract_touchpoints(system, data)
    ref = ImportRef(
        system=system,
        path=str(path),
        sha256=_sha256_file(path),
        extracted=extracted,
    )
    payload = contract.model_dump(by_alias=True)
    payload["imports"] = [
        r.model_dump(by_alias=True)
        for r in contract.imports
        if not (r.system == system and r.path == str(path))
    ] + [ref.model_dump(by_alias=True)]
    return UXContract.model_validate(payload)
