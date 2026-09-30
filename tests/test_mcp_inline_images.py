from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from pathlib import Path
from typing import Any, cast

from mcp import types
import pytest

from ux_creator import mcp_server
from ux_creator.render import RenderResult

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/smart-kettle/smart-kettle.ux.json"


def _content_payload(
    result: object,
) -> tuple[dict[str, Any], list[types.ContentBlock]]:
    assert isinstance(result, list)
    content = cast(list[types.ContentBlock], result)
    assert content and isinstance(content[0], types.TextContent)
    return cast(dict[str, Any], json.loads(content[0].text)), content


def test_render_tool_attaches_pngs_with_caps_and_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    oversized = tmp_path / "large.png"
    oversized.write_bytes(b"x" * (4 * 1024 * 1024 + 1))
    small_images = [tmp_path / f"image-{index}.png" for index in range(9)]
    for path in small_images:
        path.write_bytes(path.name.encode("ascii"))
    renders = [
        RenderResult(tmp_path / "large.mmd", oversized, "ok", ""),
        *[RenderResult(tmp_path / f"{path.stem}.mmd", path, "ok", "") for path in small_images],
    ]

    def fake_render_all(_out_dir: Path, **_kwargs: object) -> list[RenderResult]:
        return renders

    monkeypatch.setattr(mcp_server, "render_all", fake_render_all)

    result = asyncio.run(mcp_server.dispatch_tool("ux_render", {"dir": str(tmp_path)}))

    payload, content = _content_payload(result)
    metadata = payload["inline_images"]
    assert metadata[0] == {
        "path": str(oversized),
        "sha256": hashlib.sha256(oversized.read_bytes()).hexdigest(),
        "attached": False,
        "reason": "over_4_mib",
    }
    assert len([entry for entry in metadata if entry["attached"]]) == 8
    assert metadata[-1]["attached"] is False
    assert metadata[-1]["reason"] == "image_limit_reached"
    images = [block for block in content if isinstance(block, types.ImageContent)]
    assert len(images) == 8
    assert base64.b64decode(images[0].data) == small_images[0].read_bytes()
    assert payload["verdict"] == "pass"


def test_author_render_returns_text_and_inline_png(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_bytes = b"author-render-png"

    def fake_render_all(out_dir: Path, **_kwargs: Any) -> list[RenderResult]:
        out_dir.mkdir(parents=True, exist_ok=True)
        image = out_dir / "statechart.png"
        image.write_bytes(image_bytes)
        return [RenderResult(out_dir / "statechart.mmd", image, "ok", "")]

    monkeypatch.setattr(mcp_server, "render_all", fake_render_all)

    result = asyncio.run(
        mcp_server.dispatch_tool(
            "ux_author",
            {
                "contract_path": str(EXAMPLE),
                "out_dir": str(tmp_path / "author"),
                "render": True,
            },
        )
    )

    payload, content = _content_payload(result)
    images = [block for block in content if isinstance(block, types.ImageContent)]
    assert payload["verdict"] == "pass"
    assert payload["inline_images"] == [
        {
            "path": str(tmp_path / "author" / "statechart.png"),
            "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "attached": True,
        }
    ]
    assert len(images) == 1
    assert base64.b64decode(images[0].data) == image_bytes
