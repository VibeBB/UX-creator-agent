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
    _aquasecurity_version_inputs,  # pyright: ignore[reportPrivateUsage]
    _github_latest_tag,  # pyright: ignore[reportPrivateUsage]
    check_docker_args,
    check_python_versions,
    check_docker_base,
    check_github_actions,
    check_lynis_pin,
    check_workflow_tool_pins,
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


def test_docker_base_resolves_ruby_slim_tags():
    def fetch_json(url: str):
        assert "repositories/library/ruby" in url
        assert "name=-slim-trixie" in url
        return {
            "results": [
                {"name": "4.1.0-slim-trixie"},
                {"name": "4.0.9-slim-trixie"},
                {"name": "4.0-slim-trixie"},
                {"name": "slim-trixie"},
            ],
            "next": None,
        }

    statuses = check_docker_base(ROOT, fetch_json=fetch_json)
    assert len(statuses) == 1
    status = statuses[0]
    assert status.surface == "docker-base"
    assert status.name == "ruby"
    assert status.current == "4.0.7-slim-trixie"
    assert status.latest == "4.1.0-slim-trixie"
    assert status.outdated is True
    assert status.fetch_failed is False


def test_docker_base_ruby_fetch_failure_reports_fetch_failed():
    def fetch_json(url: str):
        raise OSError("network down")

    statuses = check_docker_base(ROOT, fetch_json=fetch_json)
    assert len(statuses) == 1
    status = statuses[0]
    assert status.name == "ruby"
    assert status.latest == "?"
    assert status.outdated is False
    assert status.fetch_failed is True


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


def test_github_actions_strips_subpath_action_refs(tmp_path: Path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    sha = "a" * 40
    (workflows / "lint.yml").write_text(
        f"- uses: github/codeql-action/upload-sarif@{sha} # v4.38.2\n",
        encoding="utf-8",
    )
    urls: list[str] = []

    def tags(url: str) -> list[str]:
        urls.append(url)
        return ["v4.39.0"]

    statuses = check_github_actions(tmp_path, list_remote_tags=tags)
    assert urls == ["https://github.com/github/codeql-action"]
    status = next(status for status in statuses if status.name == "github/codeql-action")
    assert status.current == "v4.38.2"
    assert status.latest == "v4.39.0"
    assert status.outdated is True


def test_aquasecurity_version_inputs_stays_inside_the_step():
    sha = "0" * 40
    text = (
        f"      - uses: aquasecurity/trivy-action@{sha} # v0.36.0\n"
        "        with:\n"
        "          scan-type: image\n"
        "          version: v0.75.0\n"
        "      - name: other\n"
        "        run: echo hi\n"
        "      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567 # v7.0.1\n"
        "        with:\n"
        "          version: v9.9.9\n"
    )
    assert _aquasecurity_version_inputs(text) == ["v0.75.0"]


def test_workflow_tool_pins_reads_direct_download_and_trivy_inputs():
    def fetch_json(url: str):
        assert "zizmor" in url
        return {"info": {"version": "1.31.0"}}

    def tags(url: str) -> list[str]:
        return {"rhysd/actionlint": ["v1.7.12"], "aquasecurity/trivy": ["v0.75.0"]}[
            url.removeprefix("https://github.com/")
        ]

    statuses = {
        status.name: status
        for status in check_workflow_tool_pins(ROOT, fetch_json=fetch_json, list_remote_tags=tags)
    }
    wheel = statuses["zizmor (wheel)"]
    assert wheel.surface == "workflow-pin"
    assert wheel.current == "1.30.1"
    assert wheel.latest == "1.31.0"
    assert wheel.outdated is True
    assert wheel.source == "workflow-lint.yml"
    tarball = statuses["actionlint (tarball)"]
    assert tarball.current == "1.7.12"
    assert tarball.latest == "v1.7.12"
    assert tarball.outdated is False
    trivy = statuses["trivy (action input)"]
    assert trivy.current == "v0.75.0"
    assert trivy.latest == "v0.75.0"
    assert trivy.outdated is False


def test_workflow_tool_pins_reports_fetch_failed():
    def fetch_json(url: str):
        raise OSError("network down")

    def timed_out(url: str) -> list[str]:
        raise subprocess.TimeoutExpired(["git", "ls-remote", "--tags", url], 1)

    statuses = check_workflow_tool_pins(ROOT, fetch_json=fetch_json, list_remote_tags=timed_out)
    assert {status.name for status in statuses} == {
        "zizmor (wheel)",
        "actionlint (tarball)",
        "trivy (action input)",
    }
    assert all(status.fetch_failed for status in statuses)
    assert all(status.latest == "?" for status in statuses)


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


def test_python_versions_skip_older_legs_when_source_covers_latest(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.12"\n', encoding="utf-8"
    )
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n  verify:\n    strategy:\n      matrix:\n        python-version: [\"3.12\", \"3.13\", \"3.14\", \"3.15\"]\n",
        encoding="utf-8",
    )
    statuses = check_python_versions(
        tmp_path, list_remote_tags=lambda url: ["v3.12.0", "v3.13.0", "v3.14.0", "v3.15.0"]
    )
    ci_statuses = [status for status in statuses if status.source.endswith("ci.yml")]
    assert ci_statuses
    assert all(not status.outdated for status in ci_statuses)


def test_python_versions_still_flag_source_without_latest(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.12"\n', encoding="utf-8"
    )
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n  verify:\n    steps:\n      - uses: actions/setup-python@x\n"
        '        with:\n          python-version: "3.12"\n',
        encoding="utf-8",
    )
    statuses = check_python_versions(
        tmp_path, list_remote_tags=lambda url: ["v3.12.0", "v3.13.0", "v3.14.0", "v3.15.0"]
    )
    ci_statuses = [status for status in statuses if status.source.endswith("ci.yml")]
    assert ci_statuses
    assert all(status.outdated for status in ci_statuses)
