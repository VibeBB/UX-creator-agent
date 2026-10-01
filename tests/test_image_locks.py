from __future__ import annotations

import json
from pathlib import Path

from scripts.print_locked_image import locked_image
from scripts.update_image_digest_lock import main as update_lock_main


def test_attestation_metadata_is_written_and_readers_accept_it(tmp_path: Path) -> None:
    lock_path = tmp_path / "image-digests.json"
    digest = f"sha256:{'a' * 64}"
    image = "ghcr.io/vibebb/ux-tools"
    attestation = "https://github.com/VibeBB/UX-creator-agent/attestations/123"
    tools_path = tmp_path / "tools.json"
    tools_path.write_text(json.dumps({"python": "Python 3.12"}), encoding="utf-8")
    args = [
        "--lock",
        str(lock_path),
        "--entry",
        "ux_tools",
        "--image",
        image,
        "--tag",
        f"{'b' * 40}-tools",
        "--digest",
        digest,
        "--published-at",
        "2026-10-01T00:00:00Z",
        "--workflow-run",
        "https://github.com/VibeBB/UX-creator-agent/actions/runs/123",
        "--dockerfile",
        "docker/ux-tools.Dockerfile",
        "--attestation",
        attestation,
        "--tools-json",
        str(tools_path),
    ]

    assert update_lock_main(args) == 0
    entry = json.loads(lock_path.read_text(encoding="utf-8"))["ux_tools"]
    assert entry["attestation"] == attestation
    assert update_lock_main(args) == 0
    assert locked_image(lock_path, "ux_tools") == f"{image}@{digest}"
