"""Fixtures through the publish/audit SARIF-gate filter.

scripts/trivy_findings.py reproduces the old second Trivy scan's
`severity: CRITICAL,HIGH` + `ignore-unfixed` result set from the single
full JSON scan; these tests pin that filter and the gate-count the
workflows branch on.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from scripts.trivy_findings import filter_report, render_summary

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "trivy_findings.py"


def _report(findings: dict[str, Any]) -> dict[str, Any]:
    return {"SchemaVersion": 2, "ArtifactName": "img", "Results": [findings]}


def _finding_block() -> dict[str, Any]:
    return {
        "Target": "debian 13",
        "Class": "os-pkgs",
        "Type": "debian",
        "Vulnerabilities": [
            {
                "VulnerabilityID": "CVE-2024-0001",
                "PkgName": "libx",
                "InstalledVersion": "1.0",
                "FixedVersion": "1.1",
                "Severity": "HIGH",
            },
            {
                "VulnerabilityID": "CVE-2024-0002",
                "PkgName": "liby",
                "InstalledVersion": "2.0",
                "Severity": "CRITICAL",
            },
            {
                "VulnerabilityID": "CVE-2024-0003",
                "PkgName": "libz",
                "InstalledVersion": "3.0",
                "FixedVersion": "3.1",
                "Severity": "MEDIUM",
            },
        ],
        "Misconfigurations": [
            {"ID": "DS-0001", "AVDID": "AVD-DS-0001", "Severity": "HIGH", "Status": "PASS"},
            {
                "ID": "DS-0002",
                "AVDID": "AVD-DS-0002",
                "Title": "Privileged container",
                "Severity": "HIGH",
                "Status": "FAIL",
            },
            {"ID": "DS-0003", "AVDID": "AVD-DS-0003", "Severity": "LOW", "Status": "FAIL"},
        ],
        "Secrets": [
            {"RuleID": "private-key", "Title": "Private key", "Severity": "CRITICAL"},
            {"RuleID": "low-secret", "Title": "token", "Severity": "LOW"},
        ],
        "Licenses": [{"Name": "MIT"}],
    }


def test_filter_report_keeps_only_the_gate_set() -> None:
    report = _report(_finding_block())
    rows = filter_report(report)
    result = cast(list[dict[str, Any]], report["Results"])[0]
    vulns = cast(list[dict[str, Any]], result["Vulnerabilities"])
    misconfigs = cast(list[dict[str, Any]], result["Misconfigurations"])
    secrets = cast(list[dict[str, Any]], result["Secrets"])
    assert [v["VulnerabilityID"] for v in vulns] == ["CVE-2024-0001"]
    assert [m["ID"] for m in misconfigs] == ["DS-0002"]
    assert [s["RuleID"] for s in secrets] == ["private-key"]
    assert "Licenses" not in result
    assert len(rows) == 3
    vuln_row = next(row for row in rows if row["scanner"] == "vuln")
    assert vuln_row["id"] == "CVE-2024-0001"
    assert vuln_row["detail"] == "1.0 -> 1.1"


def test_filter_report_clean_report_gates_zero() -> None:
    report = _report(
        {
            "Target": "img",
            "Vulnerabilities": [
                {
                    "VulnerabilityID": "CVE-2024-0002",
                    "PkgName": "liby",
                    "Severity": "CRITICAL",
                }
            ],
        }
    )
    assert filter_report(report) == []


def test_render_summary_lists_gate_failures() -> None:
    report = _report(_finding_block())
    summary = render_summary(filter_report(report))
    assert "3 fixable HIGH/CRITICAL finding(s)" in summary
    assert "| scanner | severity | id |" in summary
    assert "CVE-2024-0001" in summary
    assert "AVD-DS-0002" in summary
    assert "private-key" in summary


def test_main_writes_filtered_json_summary_and_count(tmp_path: Path) -> None:
    src = tmp_path / "trivy-image.json"
    src.write_text(json.dumps(_report(_finding_block())), encoding="utf-8")
    filtered = tmp_path / "trivy-image.filtered.json"
    summary = tmp_path / "summary.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(src),
            "--filtered",
            str(filtered),
            "--summary",
            str(summary),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "3"
    written = cast(dict[str, Any], json.loads(filtered.read_text(encoding="utf-8")))
    written_vulns = cast(
        list[dict[str, Any]], cast(list[dict[str, Any]], written["Results"])[0]["Vulnerabilities"]
    )
    assert [v["VulnerabilityID"] for v in written_vulns] == ["CVE-2024-0001"]
    assert "CVE-2024-0001" in summary.read_text(encoding="utf-8")


def test_main_writes_no_summary_when_gate_is_clean(tmp_path: Path) -> None:
    src = tmp_path / "trivy-image.json"
    src.write_text(json.dumps(_report({"Target": "img", "Vulnerabilities": []})), encoding="utf-8")
    filtered = tmp_path / "trivy-image.filtered.json"
    summary = tmp_path / "summary.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(src),
            "--filtered",
            str(filtered),
            "--summary",
            str(summary),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0"
    assert filtered.is_file()
    assert not summary.exists()
