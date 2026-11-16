"""Fail-closed release-lock and installed-interface checks."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from scripts.verify_family_install import (
    Release,
    ReleaseLock,
    install_one,
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


def test_interface_check_keeps_asset_load_separate_from_cooperation(tmp_path: Path) -> None:
    assert interface_gaps("bard", ["bard", "bard-critic"], [], tmp_path) == [
        f"missing native liaison CLI asset: scripts/{filename}"
        for filename in ("bard_cli.py", "bard_liaison.py", "bard_records.py")
    ]
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for filename in ("bard_cli.py", "bard_liaison.py", "bard_records.py"):
        (scripts / filename).write_text("# CLI asset\n", encoding="utf-8")
    assert not interface_gaps("bard", ["bard"], [], tmp_path)
    assert interface_gaps("ux", ["ux-creator"], ["ux"], tmp_path) == [
        "missing native liaison agent: ux-liaison"
    ]
    assert not interface_gaps("ux", ["ux-liaison"], ["ux"], tmp_path)
    assert interface_gaps("ux", ["ux-liaison"], [], tmp_path) == ["missing declared MCP server: ux"]


def test_installed_digest_binds_paths_bytes_and_rejects_links(tmp_path: Path) -> None:
    artifact = tmp_path / "agent.md"
    artifact.write_text("agent", encoding="utf-8")
    first = tree_sha256(tmp_path)
    artifact.rename(tmp_path / "other.md")
    assert tree_sha256(tmp_path) != first
    (tmp_path / "linked.md").symlink_to(tmp_path / "other.md")
    with pytest.raises(ValueError, match="symlink"):
        tree_sha256(tmp_path)


def test_digest_rejects_symlink_root_and_missing_tree(tmp_path: Path) -> None:
    (tmp_path / "root").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "root", target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        tree_sha256(tmp_path / "link")
    with pytest.raises(ValueError, match="unavailable"):
        tree_sha256(tmp_path / "missing")


@pytest.mark.parametrize("directory", [False, True])
def test_rejects_source_links_before_sdk_dereferences(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory: bool
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "outside"
    if directory:
        target.mkdir()
        (target / "external.md").write_text("outside plugin", encoding="utf-8")
    else:
        target.write_text("outside plugin", encoding="utf-8")
    (source / "linked").symlink_to(target, target_is_directory=directory)
    store = tmp_path / "installed"

    def copy_like_sdk(*_args: object, **_kwargs: object) -> SimpleNamespace:
        # The SDK's default copytree materializes links as ordinary files/directories.
        shutil.copytree(source, store / "ux")
        return SimpleNamespace(install_path=store / "ux", resolved_ref="a" * 40)

    installer = Mock(side_effect=copy_like_sdk)
    plugin = SimpleNamespace(
        name="ux",
        version="1.0.0",
        agents=[SimpleNamespace(name="ux-liaison")],
        commands=[],
        mcp_config={"ux": {}},
    )
    monkeypatch.setitem(
        sys.modules,
        "openhands.sdk.plugin",
        SimpleNamespace(Plugin=SimpleNamespace(load=Mock(return_value=plugin))),
    )
    monkeypatch.setitem(
        sys.modules, "openhands.sdk.plugin.installed", SimpleNamespace(install_plugin=installer)
    )
    monkeypatch.setitem(
        sys.modules,
        "openhands.sdk.extensions.fetch",
        SimpleNamespace(fetch_with_resolution=Mock(return_value=(source, "a" * 40))),
    )
    monkeypatch.setattr(
        "scripts.verify_family_install.subprocess.run",
        Mock(return_value=SimpleNamespace(stdout="a" * 40 + "\trefs/tags/v1.0.0\n")),
    )
    result = install_one(release(), store)
    assert result.status == "error"
    assert any("symlink" in gap for gap in result.gaps)
    installer.assert_not_called()
