"""Declared auxiliary ancestry scopes obligations, never product acceptance."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

import pytest

from ux_creator import mcp_server
from ux_creator.image_delivery import original_review_images, review_image_delivery
from ux_creator.render import ImageDetail, ImageIdentity, RenderResult, with_image_details
from ux_creator.review_checkpoint import review_checkpoint

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "plugins/ux/hooks/scripts"


@pytest.fixture()
def stop_hook() -> ModuleType:
    sys.path.insert(0, str(HOOKS))
    spec = importlib.util.spec_from_file_location("lineage_stop_hook", HOOKS / "require_records.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _image(root: Path, name: str, owner: Literal["ux", "bard"] = "ux") -> RenderResult:
    path = root / name
    path.write_bytes(name.encode())
    return RenderResult(
        path,
        path,
        "ok",
        "synthetic bytes, no visual perception",
        ImageIdentity(
            path=str(path),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            owner_plugin=owner,
            origin="renderer" if owner == "ux" else "liaison-response",
        ),
    )


def _details(
    root: Path, renders: list[RenderResult], *, composite: bool = False
) -> list[RenderResult]:
    (root / "tile.png").write_bytes(b"synthetic auxiliary bytes")
    return with_image_details(
        renders,
        [
            ImageDetail(
                path="tile.png",
                parents=[str(r.output) for r in renders],
                operation="composite" if composite else "tile",
            )
        ],
        root,
    )


def _deliver(root: Path, renders: list[RenderResult]) -> list[dict[str, Any]]:
    blocks = mcp_server._render_content({}, renders)  # pyright: ignore[reportPrivateUsage]
    result = subprocess.run(
        [sys.executable, str(HOOKS / "record_image_observation.py")],
        input=json.dumps(
            {
                "working_dir": str(root),
                "session_id": "native",
                "tool_name": "ux_render",
                "tool_response": {"content": [b.model_dump(by_alias=True) for b in blocks]},
            }
        ),
        env={
            k: v
            for k, v in os.environ.items()
            if k not in {"OPENHANDS_PROJECT_DIR", "UX_IMAGE_OBSERVATIONS"}
        },
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0 and not result.stderr, result.stderr
    return [
        json.loads(line)
        for line in (root / "observations/ux/image-observations.jsonl").read_text().splitlines()
    ]


def _tile(observations: list[dict[str, Any]]) -> dict[str, Any]:
    return next(row for row in observations if row["image_identity"]["origin"] == "derived")


@pytest.mark.parametrize("override", [False, True])
def test_tile_receipt_and_checkpoint_use_one_original_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stop_hook: ModuleType,
    override: bool,
) -> None:
    monkeypatch.delenv("OPENHANDS_SESSION_ID", raising=False)
    monkeypatch.delenv("UX_IMAGE_OBSERVATIONS", raising=False)
    source = _image(tmp_path, "source.png")
    assert source.image_identity is not None
    renders = _details(tmp_path, [source])
    observations = _deliver(tmp_path, renders)
    log = tmp_path / "observations/ux/image-observations.jsonl"
    tile = tmp_path / "tile.png"
    receipt = review_image_delivery(
        log, tile, hashlib.sha256(tile.read_bytes()).hexdigest(), "native"
    )
    assert receipt.status == receipt.producer_identity_status == "bound"
    assert receipt.image_identity and receipt.image_identity.origin == "derived"
    assert original_review_images(log, tile, tmp_path) == [tmp_path / "source.png"]
    assert stop_hook._observation_keys(_tile(observations), tmp_path, "ux")[0] == [
        (str(source.output), source.image_identity.sha256)
    ]
    contract = tmp_path / "contract.json"
    contract.write_text("{}")
    if override:
        custom_log = tmp_path / "custom-images.jsonl"
        custom_log.write_bytes(log.read_bytes())
        log.unlink()
        monkeypatch.setenv("UX_IMAGE_OBSERVATIONS", "custom-images.jsonl")
    checkpoint = review_checkpoint(
        {
            "action": "create",
            "checkpoint_id": "lineage",
            "session_id": "coordinator",
            "contract_path": "contract.json",
            "sources": [
                {"image_path": "source.png", "checklist": "layout"},
                {"image_path": "tile.png", "checklist": "layout"},
            ],
        },
        tmp_path,
    )
    pairs = checkpoint["pairs"]
    assert isinstance(pairs, list) and len(pairs) == 2
    assert checkpoint["acceptance"] == "unknown"


def test_multisource_preserves_each_parent_owner(tmp_path: Path, stop_hook: ModuleType) -> None:
    roots = [_image(tmp_path, "ux.png"), _image(tmp_path, "bard.png", "bard")]
    observations = _deliver(tmp_path, _details(tmp_path, roots, composite=True))
    tile = _tile(observations)
    for owner, source in zip(("ux", "bard"), roots, strict=True):
        assert source.image_identity is not None
        assert stop_hook._observation_keys(tile, tmp_path, owner)[0] == [
            (str(source.output), source.image_identity.sha256)
        ]
    assert stop_hook._observation_keys(tile, tmp_path, "wire")[0] == []


@pytest.mark.parametrize("damage", ["parent", "child", "copy", "forged_owner", "outside"])
def test_changed_or_unverified_lineage_never_waives_review(
    tmp_path: Path,
    stop_hook: ModuleType,
    damage: str,
) -> None:
    observations = _deliver(tmp_path, _details(tmp_path, [_image(tmp_path, "source.png")]))
    tile = _tile(observations)
    if damage == "parent":
        (tmp_path / "source.png").write_bytes(b"new source revision")
    elif damage == "child":
        (tmp_path / "tile.png").write_bytes(b"new auxiliary revision")
    elif damage == "copy":
        copied = tmp_path / "copy.png"
        copied.write_bytes((tmp_path / "tile.png").read_bytes())
        tile["image_path"] = str(copied)
    elif damage == "outside":
        tile["image_identity"]["parents"][0]["path"] = "/etc/hosts"
    else:
        tile["image_identity"]["parents"][0]["owner_plugin"] = "wire"
    keys, warning = stop_hook._observation_keys(tile, tmp_path, "ux")
    assert len(keys) == 1 and warning and "unknown" in warning
    assert keys[0][0] == tile["image_path"]


def test_changed_parent_blocks_checkpoint_reuse(tmp_path: Path) -> None:
    _deliver(tmp_path, _details(tmp_path, [_image(tmp_path, "source.png")]))
    (tmp_path / "source.png").write_bytes(b"new source revision")
    with pytest.raises(ValueError, match="original revision changed"):
        original_review_images(
            tmp_path / "observations/ux/image-observations.jsonl", tmp_path / "tile.png", tmp_path
        )


def test_formal_changed_source_requires_new_hash(tmp_path: Path, stop_hook: ModuleType) -> None:
    observation = _deliver(tmp_path, [_image(tmp_path, "source.png")])[0]
    (tmp_path / "source.png").write_bytes(b"new formal revision")
    keys, warning = stop_hook._observation_keys(observation, tmp_path, "ux")
    assert warning and "unknown" in warning
    assert keys == [
        (str(tmp_path / "source.png"), hashlib.sha256(b"new formal revision").hexdigest())
    ]


def test_producer_rejects_unrelated_copied_and_recursive_parents(tmp_path: Path) -> None:
    source = _image(tmp_path, "source.png")
    (tmp_path / "tile.png").write_bytes(b"detail")
    for parents in (["missing.png"], ["source.png", "source.png"], ["tile.png"]):
        with pytest.raises((ValueError, OSError)):
            with_image_details(
                [source],
                [ImageDetail(path="tile.png", parents=parents, operation="composite")],
                tmp_path,
            )


def test_missing_original_review_survives_auxiliary_dedup(
    tmp_path: Path, stop_hook: ModuleType
) -> None:
    source = _image(tmp_path, "source.png")
    tile = _tile(_deliver(tmp_path, _details(tmp_path, [source])))
    keys, _ = stop_hook._observation_keys(tile, tmp_path, "ux")
    assert keys and keys[0][0] == str(source.output)
    review = {"image_path": "tile.png", "image_sha256": tile["image_sha256"]}
    assert stop_hook._image_key(review, tmp_path) not in keys


def test_requested_composite_is_delivered_before_eight_originals(tmp_path: Path) -> None:
    renders = _details(
        tmp_path, [_image(tmp_path, f"source-{i}.png") for i in range(8)], composite=True
    )
    observations = _deliver(tmp_path, renders)
    assert len(observations) == 8
    assert _tile(observations)["identity_status"] == "bound"
