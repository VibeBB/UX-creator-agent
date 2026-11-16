"""Fail-closed release-lock and installed-interface checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts.verify_family_install import (
    Release,
    ReleaseLock,
    interface_gaps,
    tree_sha256,
    verify_tag_output,
)


def release(**changes: str) -> Release:
    return Release.model_validate(
        {
            "plugin": "ux",
            "repository": "VibeBB/UX-creator-agent",
            "source_commit": "a" * 40,
            "release": "v1.0.0",
            "release_url": "https://github.com/VibeBB/UX-creator-agent/releases/tag/v1.0.0",
            "published_at": "2026-11-15T00:00:00Z",
            "repo_path": "plugins/ux",
            **changes,
        }
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"repository": "external/UX-creator-agent"},
        {"repo_path": "../plugins/ux"},
        {"plugin": "unknown"},
        {"source_commit": "main"},
        {"release_url": "https://example.com/v1.0.0"},
        {"release": "main"},
    ],
)
def test_rejects_unpinned_or_external_sources(changes: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        release(**changes)


def test_family_lock_cannot_omit_or_duplicate_plugins() -> None:
    with pytest.raises(ValidationError, match="each of the eleven"):
        ReleaseLock(
            schema_version=1,
            scope="release-pinned-plugin-installation",
            plugins=[release()] * 11,
        )


def test_tag_validation_checks_annotated_commit_not_tag_object() -> None:
    entry = release()
    verify_tag_output(entry, "a" * 40 + "\trefs/tags/v1.0.0\n")
    verify_tag_output(
        entry,
        "b" * 40 + "\trefs/tags/v1.0.0\n" + "a" * 40 + "\trefs/tags/v1.0.0^{}\n",
    )
    with pytest.raises(ValueError, match="does not resolve"):
        verify_tag_output(
            entry, "a" * 40 + "\trefs/tags/v1.0.0\n" + "b" * 40 + "\trefs/tags/v1.0.0^{}\n"
        )
    with pytest.raises(ValueError, match="does not resolve"):
        verify_tag_output(entry, "")


def test_interface_check_keeps_asset_load_separate_from_cooperation() -> None:
    assert interface_gaps("bard", ["bard", "bard-critic"], []) == [
        "missing declared MCP server: bard"
    ]
    assert interface_gaps("ux", ["ux-creator"], ["ux"]) == [
        "missing native liaison agent: ux-liaison"
    ]
    assert not interface_gaps("ux", ["ux-liaison"], ["ux"])


def test_installed_digest_binds_paths_bytes_and_rejects_links(tmp_path: Path) -> None:
    artifact = tmp_path / "agent.md"
    artifact.write_text("agent", encoding="utf-8")
    first = tree_sha256(tmp_path)
    artifact.rename(tmp_path / "other.md")
    assert tree_sha256(tmp_path) != first
    (tmp_path / "linked.md").symlink_to(tmp_path / "other.md")
    with pytest.raises(ValueError, match="symlink"):
        tree_sha256(tmp_path)
