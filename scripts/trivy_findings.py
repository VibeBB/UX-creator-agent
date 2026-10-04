#!/usr/bin/env python3
"""Filter a full Trivy JSON report down to the SARIF/gate result set.

publish-ux-images.yml and container-audit.yml scan each image once with
every scanner at every severity (the full JSON is uploaded as the audit
artifact). The SARIF upload — and, in publish, the release gate — used to
come from a second scan run with `severity: CRITICAL,HIGH` and
`ignore-unfixed: true`. This script reproduces that filtered result set
from the full JSON: it writes a filtered report that `trivy convert`
renders into the same SARIF the second scan produced, prints the finding
count for the workflow to gate on, and optionally appends a markdown
table to a step-summary file for one-glance triage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

GATE_SEVERITIES = {"CRITICAL", "HIGH"}
SUMMARY_ROW_LIMIT = 40


def _entries(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return cast(list[dict[str, Any]], value)


def filter_report(report: dict[str, Any]) -> list[dict[str, str]]:
    """Subset a trivy JSON report to the gate set, in place.

    Returns the kept findings as rows for the step summary. The filtered
    report keeps every other field (Class, Type, Target, MisconfSummary)
    so `trivy convert` renders SARIF from it unchanged.
    """
    rows: list[dict[str, str]] = []
    for result in _entries(report.get("Results")):
        target = str(result.get("Target", ""))
        vulns = [
            vuln
            for vuln in _entries(result.get("Vulnerabilities"))
            if str(vuln.get("Severity", "")) in GATE_SEVERITIES and vuln.get("FixedVersion")
        ]
        misconfigs = [
            misconfig
            for misconfig in _entries(result.get("Misconfigurations"))
            if str(misconfig.get("Severity", "")) in GATE_SEVERITIES
            and misconfig.get("Status") == "FAIL"
        ]
        secrets = [
            secret
            for secret in _entries(result.get("Secrets"))
            if str(secret.get("Severity", "")) in GATE_SEVERITIES
        ]
        result["Vulnerabilities"] = vulns
        result["Misconfigurations"] = misconfigs
        result["Secrets"] = secrets
        result.pop("Licenses", None)
        for vuln in vulns:
            rows.append(
                {
                    "scanner": "vuln",
                    "severity": str(vuln.get("Severity", "")),
                    "id": str(vuln.get("VulnerabilityID", "?")),
                    "target": str(vuln.get("PkgName", "?")),
                    "detail": f"{vuln.get('InstalledVersion', '?')} -> "
                    f"{vuln.get('FixedVersion', '?')}",
                }
            )
        for misconfig in misconfigs:
            rows.append(
                {
                    "scanner": "misconfig",
                    "severity": str(misconfig.get("Severity", "")),
                    "id": str(misconfig.get("AVDID") or misconfig.get("ID", "?")),
                    "target": target,
                    "detail": str(misconfig.get("Title", ""))[:80],
                }
            )
        for secret in secrets:
            rows.append(
                {
                    "scanner": "secret",
                    "severity": str(secret.get("Severity", "")),
                    "id": str(secret.get("RuleID", "?")),
                    "target": target,
                    "detail": str(secret.get("Title", ""))[:80],
                }
            )
    return rows


def render_summary(rows: list[dict[str, str]]) -> str:
    severity_order = {"CRITICAL": 0, "HIGH": 1}
    ordered = sorted(rows, key=lambda row: (severity_order.get(row["severity"], 2), row["id"]))
    lines = [
        f"## Trivy gate: {len(rows)} fixable HIGH/CRITICAL finding(s)",
        "",
        "| scanner | severity | id | package/target | detail |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in ordered[:SUMMARY_ROW_LIMIT]:
        lines.append(
            f"| {row['scanner']} | {row['severity']} | {row['id']} "
            f"| {row['target']} | {row['detail']} |"
        )
    if len(ordered) > SUMMARY_ROW_LIMIT:
        lines.append(f"| … | | +{len(ordered) - SUMMARY_ROW_LIMIT} more | | |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="full trivy JSON report")
    parser.add_argument("--filtered", type=Path, required=True, help="filtered JSON output path")
    parser.add_argument("--summary", type=Path, help="append the findings table to this file")
    args = parser.parse_args(argv)
    report = cast(dict[str, Any], json.loads(args.input.read_text(encoding="utf-8")))
    rows = filter_report(report)
    args.filtered.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.summary is not None and rows:
        with args.summary.open("a", encoding="utf-8") as stream:
            stream.write(render_summary(rows))
    print(len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
