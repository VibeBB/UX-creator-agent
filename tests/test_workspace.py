from __future__ import annotations

from pathlib import Path

import pytest

from ux_creator.workspace import reject_symlinks, workspace_path


def test_workspace_path_resolves_normal_relative_path(tmp_path: Path) -> None:
    child = tmp_path / "workspace" / "contract.json"
    child.parent.mkdir()
    child.touch()
    assert workspace_path("workspace/contract.json", tmp_path) == child.resolve()


def test_workspace_path_rejects_parent_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside the workspace"):
        workspace_path("../outside.json", tmp_path)


def test_workspace_path_rejects_absolute_path_outside_root(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.json"
    with pytest.raises(ValueError, match="outside the workspace"):
        workspace_path(outside, tmp_path)


def test_workspace_path_rejects_symlink_component(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (tmp_path / "linked").symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="contains a symlink"):
        workspace_path("linked/file.json", tmp_path)


def test_reject_symlinks_rejects_symlink_paths(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="is a symlink"):
        reject_symlinks(link)
