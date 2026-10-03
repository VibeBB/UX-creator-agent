from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import scripts.check_dependency_updates as check_dependency_updates_module
from scripts.check_dependency_updates import (
    HTTP_TIMEOUT_SECONDS,
    ROOT,
    SUBPROCESS_TIMEOUT_SECONDS,
    DependencyStatus,
    _github_latest_tag,  # pyright: ignore[reportPrivateUsage]
    check_docker_args,
    check_lynis_pin,
    main,
)


def test_github_latest_tag_treats_timeout_as_fetch_failure():
    def timed_out(url: str) -> list[str]:
        raise subprocess.TimeoutExpired(["git", "ls-remote", "--tags", url], 1)

    assert _github_latest_tag("actions/checkout", timed_out) == ""


def test_github_latest_tag_matches_prefixed_multi_segment_tags():
    def tags(url: str) -> list[str]:
        return ["jdk-27.0-m1", "jdk-27.0.0.0", "jdk-27.0.0.0-m1a", "jdk-27.0.1.0-m1"]

    latest = _github_latest_tag("ibmruntimes/semeru27-binaries", tags, prefix="jdk-")
    assert latest == "jdk-27.0.0.0"


def test_docker_args_report_fetch_failed_on_timeout():
    def timed_out(url: str) -> list[str]:
        raise subprocess.TimeoutExpired(["git", "ls-remote", "--tags", url], 1)

    statuses = check_docker_args(ROOT, list_remote_tags=timed_out)
    uv_status = next(status for status in statuses if status.name == "UV_VERSION")
    assert uv_status.latest == "?"
    assert uv_status.note == "fetch failed"
    assert uv_status.outdated is False
    assert uv_status.fetch_failed is True


def test_lynis_pin_reads_audit_clone_branch():
    def tags(url: str) -> list[str]:
        assert url == "https://github.com/CISOfy/lynis"
        return ["3.0.8", "3.1.7", "3.1.9"]

    statuses = check_lynis_pin(ROOT, list_remote_tags=tags)
    assert len(statuses) == 1
    status = statuses[0]
    assert status.surface == "workflow-pin"
    assert status.name == "lynis"
    assert status.current == "3.1.7"
    assert status.latest == "3.1.9"
    assert status.outdated is True
    assert status.fetch_failed is False


def test_lynis_pin_reports_fetch_failed_on_timeout():
    def timed_out(url: str) -> list[str]:
        raise subprocess.TimeoutExpired(["git", "ls-remote", "--tags", url], 1)

    statuses = check_lynis_pin(ROOT, list_remote_tags=timed_out)
    assert len(statuses) == 1
    status = statuses[0]
    assert status.latest == "?"
    assert status.note == "fetch failed"
    assert status.outdated is False
    assert status.fetch_failed is True


def test_subprocess_timeout_is_bounded():
    assert SUBPROCESS_TIMEOUT_SECONDS >= HTTP_TIMEOUT_SECONDS > 0


def test_main_reports_timeout_as_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    def timed_out(repo_root: Path) -> list[DependencyStatus]:
        raise subprocess.TimeoutExpired(["uv", "lock"], SUBPROCESS_TIMEOUT_SECONDS)

    monkeypatch.setattr(check_dependency_updates_module, "check_dependency_updates", timed_out)
    assert main([]) == 1
    assert "dependency update check failed" in capsys.readouterr().err


def test_main_reports_fetch_failures_as_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fetch_failed(_repo_root: Path) -> list[DependencyStatus]:
        return [
            DependencyStatus(
                "github-actions",
                "actions/checkout",
                "sha-pinned",
                "?",
                ".github/workflows",
                False,
                "fetch failed",
                fetch_failed=True,
            )
        ]

    report_path = tmp_path / "report.json"
    monkeypatch.setattr(check_dependency_updates_module, "check_dependency_updates", fetch_failed)
    assert main(["--json", str(report_path)]) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["unknown_count"] == 1
