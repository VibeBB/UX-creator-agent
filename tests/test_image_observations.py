"""Delivery evidence for the repo-specific image observation hook."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ux_creator.image_delivery import review_image_delivery

HOOK = Path(__file__).parents[1] / "plugins/ux/hooks/scripts/record_image_observation.py"


def test_delivery_reference_is_bound_to_returned_revision_and_native_session(
    tmp_path: Path,
) -> None:
    image = tmp_path / "drawing.png"
    image.write_bytes(b"returned-drawing")
    observation = _observe(tmp_path, _payload(tmp_path, [_metadata(image)], [image.read_bytes()]))[
        0
    ]
    log = tmp_path / "observations/ux/image-observations.jsonl"
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    delivery = review_image_delivery(log, image, digest, "native-viewer-session")
    assert delivery.status == "bound"
    assert delivery.observation_event_id == observation["event_id"]
    assert delivery.tool_call_id == "native-call-1"
    assert delivery.producer_identity_status == "bound"
    assert delivery.image_identity is not None
    assert delivery.image_identity.owner_plugin == "ux"
    assert delivery.scope == "tool-return"

    assert review_image_delivery(log, image, digest, "another-session").status == "unknown"
    assert review_image_delivery(log, image, digest, None).status == "unknown"
    copied = tmp_path / "copied.png"
    copied.write_bytes(image.read_bytes())
    assert review_image_delivery(log, copied, digest, "native-viewer-session").status == "unknown"
    image.write_bytes(b"rewritten-after-return")
    current = hashlib.sha256(image.read_bytes()).hexdigest()
    assert review_image_delivery(log, image, current, "native-viewer-session").status == "unknown"
    image.unlink()
    # The source log still proves which revision was delivered, not the current file.
    assert review_image_delivery(log, image, digest, "native-viewer-session") == delivery


@pytest.mark.parametrize(
    "damage", ["digest", "session", "sequence", "json", "utf8", "deep_json", "large_integer"]
)
def test_delivery_reference_preserves_corrupt_log_as_unknown(tmp_path: Path, damage: str) -> None:
    image = tmp_path / "drawing.png"
    image.write_bytes(b"drawing")
    observation = _observe(tmp_path, _payload(tmp_path, [_metadata(image)], [image.read_bytes()]))[
        0
    ]
    log = tmp_path / "observations/ux/image-observations.jsonl"
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    if damage == "json":
        with log.open("a", encoding="utf-8") as stream:
            stream.write("{broken\n")
    elif damage == "utf8":
        log.write_bytes(b"\xff")
    elif damage == "deep_json":
        log.write_text('{"actor":' + "[" * 2000 + "0" + "]" * 2000 + "}", encoding="utf-8")
    elif damage == "large_integer":
        log.write_text('{"sequence":' + "1" * 5000 + "}", encoding="utf-8")
    elif damage == "sequence":
        with log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(observation) + "\n")
    else:
        observation["image_sha256" if damage == "digest" else "session_id"] = (
            "0" * 64 if damage == "digest" else "another-session"
        )
        log.write_text(json.dumps(observation) + "\n", encoding="utf-8")
    assert review_image_delivery(log, image, digest, "native-viewer-session").status == "unknown"


def test_file_editor_delivery_does_not_infer_producer_ownership(tmp_path: Path) -> None:
    image = tmp_path / "ux-owned-looking.png"
    image.write_bytes(b"unidentified-owner")
    payload = _payload(tmp_path, [], [image.read_bytes()], "file_editor")
    payload["tool_input"] = {"command": "view", "path": str(image)}
    _observe(tmp_path, payload)
    delivery = review_image_delivery(
        tmp_path / "observations/ux/image-observations.jsonl",
        image,
        hashlib.sha256(image.read_bytes()).hexdigest(),
        "native-viewer-session",
    )
    assert delivery.status == "bound"
    assert delivery.producer_identity_status == "unknown"
    assert delivery.image_identity is None


def test_repeated_delivery_keeps_the_first_consistent_receipt(tmp_path: Path) -> None:
    image = tmp_path / "drawing.png"
    image.write_bytes(b"same-path-and-revision")
    payload = _payload(tmp_path, [_metadata(image)], [image.read_bytes()])
    _observe(tmp_path, payload)
    payload["tool_call_id"] = "another-call"
    assert len(_observe(tmp_path, payload)) == 2
    delivery = review_image_delivery(
        tmp_path / "observations/ux/image-observations.jsonl",
        image,
        hashlib.sha256(image.read_bytes()).hexdigest(),
        "native-viewer-session",
    )
    assert delivery.status == "bound"
    assert delivery.observation_event_id is not None


def test_legacy_filename_record_is_not_delivery(tmp_path: Path) -> None:
    image = tmp_path / "drawing.png"
    image.write_bytes(b"not-delivered")
    log = tmp_path / "observations.jsonl"
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    log.write_text(
        json.dumps(
            {
                "image_path": str(image),
                "image_sha256": digest,
                "session_id": "native-viewer-session",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    delivery = review_image_delivery(log, image, digest, "native-viewer-session")
    assert delivery.status == "unknown"
    assert delivery.reason == "no_matching_delivery"


def _identity(image: Path, owner: str = "ux") -> dict[str, object]:
    return {
        "path": str(image.resolve()),
        "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "owner_plugin": owner,
        "origin": "renderer" if owner == "ux" else "liaison-response",
    }


def _metadata(image: Path, owner: str = "ux", *, attached: bool = True) -> dict[str, object]:
    return {
        "path": str(image),
        "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "attached": attached,
        "identity_status": "bound",
        "image_identity": _identity(image, owner),
    }


def _payload(
    root: Path,
    metadata: list[dict[str, object]],
    delivered: list[bytes],
    tool_name: str = "ux_render",
) -> dict[str, object]:
    return {
        "working_dir": str(root),
        "session_id": "native-viewer-session",
        "tool_call_id": "native-call-1",
        "tool_name": tool_name,
        "tool_response": {
            "content": [
                {"type": "text", "text": "[Tool executed.]"},
                {"type": "text", "text": json.dumps({"inline_images": metadata})},
                *[
                    {
                        "type": "image",
                        "image_urls": [
                            "data:image/png;base64," + base64.b64encode(data).decode("ascii")
                        ],
                    }
                    for data in delivered
                ],
            ],
            "is_error": False,
        },
    }


def _observe(root: Path, payload: dict[str, object]) -> list[dict[str, object]]:
    env = dict(os.environ)
    env.pop("OPENHANDS_PROJECT_DIR", None)
    env.pop("UX_IMAGE_OBSERVATIONS", None)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    log = root / "observations/ux/image-observations.jsonl"
    return (
        [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        if (log.exists())
        else []
    )


@pytest.mark.parametrize("tool", ["ux_render", "ux_author", "ux_produce", "ux_liaison_status"])
@pytest.mark.parametrize("prefix", ["", "ux_"])
def test_records_delivered_owner_and_native_observer(
    tmp_path: Path, tool: str, prefix: str
) -> None:
    image = tmp_path / "ux-looking-statechart.png"
    image.write_bytes(b"sister-image")
    metadata = _metadata(image, "mech")
    records = _observe(
        tmp_path, _payload(tmp_path, [metadata], [image.read_bytes()], prefix + tool)
    )
    assert len(records) == 1
    record = records[0]
    assert record["image_identity"] == metadata["image_identity"]
    assert record["identity_status"] == "bound"
    assert record["image_path"] == str(image)
    assert record["image_sha256"] == metadata["sha256"]
    assert record["session_id"] == "native-viewer-session"
    assert record["tool_call_id"] == "native-call-1"


def test_withheld_paths_are_not_observations(tmp_path: Path) -> None:
    withheld = tmp_path / "withheld.png"
    attached = tmp_path / "attached.png"
    withheld.write_bytes(b"over-cap-or-mismatched")
    attached.write_bytes(b"delivered")
    metadata = [_metadata(withheld, attached=False), _metadata(attached)]
    records = _observe(tmp_path, _payload(tmp_path, metadata, [attached.read_bytes()]))
    assert [record["image_path"] for record in records] == [str(attached)]


@pytest.mark.parametrize("delivered", [[], [b"different-image"]])
def test_metadata_without_matching_bytes_is_not_a_path_observation(
    tmp_path: Path, delivered: list[bytes]
) -> None:
    image = tmp_path / "claimed.png"
    image.write_bytes(b"claimed-image")
    records = _observe(tmp_path, _payload(tmp_path, [_metadata(image)], delivered))
    assert all(record["image_path"] is None for record in records)
    assert len(records) == len(delivered)
    assert all(record["identity_status"] == "unknown" for record in records)


@pytest.mark.parametrize("change", ["rewrite", "delete"])
def test_post_return_file_changes_preserve_the_delivered_revision(
    tmp_path: Path, change: str
) -> None:
    image = tmp_path / "returned.png"
    image.write_bytes(b"original-returned-image")
    metadata = _metadata(image)
    payload = _payload(tmp_path, [metadata], [image.read_bytes()])
    if change == "rewrite":
        image.write_bytes(b"a-revision-the-viewer-never-received")
    else:
        image.unlink()
    records = _observe(tmp_path, payload)
    assert len(records) == 1
    assert records[0]["image_sha256"] == metadata["sha256"]
    assert records[0]["image_identity"] == metadata["image_identity"]


@pytest.mark.parametrize("invalid", ["absent", "owner", "sha256", "extra", "relative", "copy"])
def test_unusable_producer_identity_remains_unknown(tmp_path: Path, invalid: str) -> None:
    image = tmp_path / "ux.statechart.png"
    image.write_bytes(b"legacy-or-invalid-claim")
    metadata = _metadata(image)
    identity = _identity(image)
    if invalid == "absent":
        metadata.pop("image_identity")
        metadata.pop("identity_status")
    else:
        if invalid == "owner":
            identity["owner_plugin"] = "unregistered-agent"
        elif invalid == "sha256":
            identity["sha256"] = "0" * 64
        elif invalid == "extra":
            identity["guessed"] = True
        elif invalid == "relative":
            identity["path"] = "ux.statechart.png"
        else:
            identity["path"] = str(tmp_path / "different-copy.png")
        metadata["image_identity"] = identity
    records = _observe(tmp_path, _payload(tmp_path, [metadata], [image.read_bytes()]))
    assert len(records) == 1
    assert records[0]["image_identity"] is None
    assert records[0]["identity_status"] == "unknown"


def test_each_delivered_occurrence_is_matched_once(tmp_path: Path) -> None:
    image = tmp_path / "one.png"
    copy = tmp_path / "two.png"
    image.write_bytes(b"same-bytes")
    copy.write_bytes(image.read_bytes())
    records = _observe(
        tmp_path,
        _payload(tmp_path, [_metadata(image), _metadata(copy)], [image.read_bytes()]),
    )
    assert len(records) == 1
    assert records[0]["image_path"] == str(image)


@pytest.mark.parametrize("change", ["none", "rewrite", "delete"])
def test_file_editor_records_returned_bytes_without_guessing_owner(
    tmp_path: Path, change: str
) -> None:
    image = tmp_path / "ux.statechart.png"
    image.write_bytes(b"file-editor-returned-revision")
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    payload = _payload(tmp_path, [], [image.read_bytes()], "file_editor")
    payload["tool_input"] = {"command": "view", "path": str(image)}
    if change == "rewrite":
        image.write_bytes(b"later-unseen-revision")
    elif change == "delete":
        image.unlink()
    records = _observe(tmp_path, payload)
    assert len(records) == 1
    assert records[0]["image_path"] == str(image)
    assert records[0]["image_sha256"] == digest
    assert records[0]["image_identity"] is None
    assert records[0]["identity_status"] == "unknown"


def test_text_only_path_does_not_establish_delivery(tmp_path: Path) -> None:
    image = tmp_path / "mentioned-only.png"
    image.write_bytes(b"never-returned")
    payload = _payload(tmp_path, [], [])
    payload["tool_response"] = {"content": [{"type": "text", "text": str(image)}]}
    assert _observe(tmp_path, payload) == []


@pytest.mark.parametrize("wire", ["mcp", "mcp-python", "malformed", "remote", "error", "bad_path"])
def test_content_formats_and_unusable_deliveries(tmp_path: Path, wire: str) -> None:
    image = tmp_path / "delivered.png"
    image.write_bytes(b"actual-image-content")
    metadata = _metadata(image)
    content: list[dict[str, object]] = [
        {"type": "text", "text": json.dumps({"inline_images": [metadata]})}
    ]
    response: dict[str, object] = {"content": content}
    if wire in {"mcp", "mcp-python"}:
        content.append(
            {
                "type": "image",
                "mimeType": "image/png",
                "data": base64.b64encode(image.read_bytes()).decode("ascii"),
            }
        )
        if wire == "mcp-python":
            content[-1]["mime_type"] = content[-1].pop("mimeType")
    elif wire == "malformed":
        content.append({"type": "image", "image_urls": ["data:image/png;base64,###"]})
    elif wire == "remote":
        content.append({"type": "image", "image_urls": ["https://invalid.example/image.png"]})
    else:
        content.append(
            {
                "type": "image",
                "image_urls": [
                    "data:image/png;base64," + base64.b64encode(image.read_bytes()).decode("ascii")
                ],
            }
        )
        if wire == "error":
            response["is_error"] = True
        else:
            metadata["path"] = "\x00.png"
            content[0]["text"] = json.dumps({"inline_images": [metadata]})
    payload = _payload(tmp_path, [], [])
    payload["tool_response"] = response
    records = _observe(tmp_path, payload)
    if wire in {"mcp", "mcp-python"}:
        assert len(records) == 1
        assert records[0]["identity_status"] == "bound"
    elif wire == "bad_path":
        assert len(records) == 1
        assert records[0]["image_path"] is None
        assert records[0]["identity_status"] == "unknown"
    else:
        assert records == []


def test_unassociated_delivery_remains_a_gap_after_bounded_stop(tmp_path: Path) -> None:
    session = "native-viewer-session"
    env = dict(os.environ)
    env["OPENHANDS_PROJECT_DIR"] = str(tmp_path)
    stop_hook = HOOK.with_name("require_records.py")
    payload = {"working_dir": str(tmp_path), "session_id": session}

    def invoke(action: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(stop_hook), action],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    assert invoke("record-context").returncode == 0
    records = _observe(tmp_path, _payload(tmp_path, [], [b"unassociated-image"]))
    assert len(records) == 1
    assert records[0]["image_path"] is None
    assert [invoke("stop").returncode for _ in range(3)] == [2, 2, 0]
    status_path = tmp_path / f"observations/ux/.sessions/{session}.status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["stop_permission"] == "allow"
    assert status["record_compliance"] == "fail"
    assert status["run_completion"] == status["acceptance"] == "unknown"
    assert any("viewed image None" in problem for problem in status["problems"])
