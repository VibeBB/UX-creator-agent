"""Feed captured Trivy JSON fixtures through the audit's report snippet.

container-audit.yml computes the weekly "Container hardening report"
inside an inline `python3 - <<'PY'` block. These tests extract that exact
snippet from the workflow file and run it against fixtures — including
the nested MisconfSummary walk that the dead-metric fix landed for.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "container-audit.yml"


def _audit_report_snippet() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.index("- name: Compute container-hardening report")
    start = text.index("python3 - <<'PY'", step) + len("python3 - <<'PY'")
    end = text.index("\n          PY", start)
    return textwrap.dedent(text[start:end])


def _run_snippet(
    tmp_path: Path, trivy: dict[str, Any], cis: dict[str, Any], lynis: str
) -> tuple[subprocess.CompletedProcess[str], Path]:
    trivy_json = tmp_path / "trivy-image.json"
    trivy_json.write_text(json.dumps(trivy), encoding="utf-8")
    cis_json = tmp_path / "trivy-cis.json"
    cis_json.write_text(json.dumps(cis), encoding="utf-8")
    lynis_out = tmp_path / "lynis-out"
    lynis_out.mkdir()
    (lynis_out / "lynis-report.dat").write_text(lynis, encoding="utf-8")
    report_json = tmp_path / "container-hardening.json"
    env = os.environ.copy()
    env.update(
        {
            "TRIVY_JSON": str(trivy_json),
            "TRIVY_CIS": str(cis_json),
            "LYNIS_OUT": str(lynis_out),
            "REPORT_JSON": str(report_json),
            "PINNED_IMAGE": "ghcr.io/vibebb/ux-tools@sha256:" + "0" * 64,
        }
    )
    script = tmp_path / "snippet.py"
    script.write_text(_audit_report_snippet(), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    return result, report_json


def _trivy_fixture() -> dict[str, Any]:
    return {
        "Results": [
            {
                "Target": "debian 13",
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-2024-0001",
                        "PkgName": "libx",
                        "FixedVersion": "1.1",
                        "Severity": "HIGH",
                    },
                    {"VulnerabilityID": "CVE-2024-0002", "PkgName": "liby", "Severity": "LOW"},
                ],
                "Misconfigurations": [
                    {"ID": "DS-0001", "Severity": "HIGH", "Status": "PASS"},
                    {"ID": "DS-0002", "Severity": "HIGH", "Status": "FAIL"},
                ],
                "Secrets": [{"RuleID": "private-key", "Severity": "CRITICAL"}],
                "Licenses": [{"Name": "MIT"}, {"Name": "Apache-2.0"}],
            }
        ]
    }


def _cis_fixture() -> dict[str, Any]:
    # `trivy --compliance` nests each control's check summaries inside the
    # control Results; every depth must be walked.
    return {
        "Results": [
            {
                "ID": "docker-cis-1.6.0",
                "Results": [
                    {"ID": "4.1", "MisconfSummary": {"Successes": 3, "Failures": 0}},
                    {
                        "ID": "4.x",
                        "Results": [
                            {"ID": "4.x.1", "MisconfSummary": {"Successes": 0, "Failures": 1}}
                        ],
                    },
                ],
            }
        ]
    }


def test_audit_report_counts_nested_cis_summaries(tmp_path: Path) -> None:
    result, report_json = _run_snippet(
        tmp_path,
        _trivy_fixture(),
        _cis_fixture(),
        "hardening_index=72\nwarning[]=warn one\nwarning[]=warn two\n",
    )
    assert result.returncode == 0, result.stderr
    report = cast(dict[str, Any], json.loads(report_json.read_text(encoding="utf-8")))
    assert report["cis_docker"] == {"passed": 3, "failed": 1}
    assert report["trivy"]["fixable_high_or_critical"] == 1
    assert report["trivy"]["misconfig_pass"] == 1
    assert report["trivy"]["misconfig_total"] == 2
    assert report["trivy"]["secrets"] == 1
    assert report["trivy"]["license_findings"] == 2
    assert report["lynis"] == {"hardening_index": "72", "warnings": 2}
    assert report["image"] == "ghcr.io/vibebb/ux-tools"
    assert report["digest"] == "sha256:" + "0" * 64


def test_audit_report_fails_on_dead_cis_payload(tmp_path: Path) -> None:
    result, _ = _run_snippet(
        tmp_path,
        _trivy_fixture(),
        {"Results": [{"ID": "docker-cis-1.6.0", "Results": []}]},
        "hardening_index=72\n",
    )
    assert result.returncode != 0
    assert "no results" in result.stderr


def test_audit_report_tolerates_missing_lynis_output(tmp_path: Path) -> None:
    result, report_json = _run_snippet(tmp_path, _trivy_fixture(), _cis_fixture(), "")
    assert result.returncode == 0, result.stderr
    report = cast(dict[str, Any], json.loads(report_json.read_text(encoding="utf-8")))
    assert cast(dict[str, Any], report["lynis"])["hardening_index"] == "unknown"
