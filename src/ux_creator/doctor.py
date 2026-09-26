"""Environment doctor: probe the tools the pipeline depends on.

Every check reports "pass" (capability present) or "fail" (missing/broken).
The verdict is fail-closed: any failed capability fails the report.
"""

from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class DoctorCheck:
    capability: str
    status: Literal["pass", "fail"]
    detail: str


def _probe_module(name: str) -> DoctorCheck:
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        return DoctorCheck(name, "fail", f"import failed: {exc}")
    version = getattr(module, "__version__", "unknown")
    return DoctorCheck(name, "pass", f"{name} {version}")


def _probe_command(cmd: str, *args: str) -> DoctorCheck:
    path = shutil.which(cmd)
    if path is None:
        return DoctorCheck(cmd, "fail", f"{cmd} not on PATH")
    try:
        proc = subprocess.run(
            [path, *args], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return DoctorCheck(cmd, "fail", f"probe failed: {exc}")
    out = (proc.stdout or proc.stderr).strip().splitlines()
    detail = out[0] if out else f"exit {proc.returncode}"
    status: Literal["pass", "fail"] = "pass" if proc.returncode == 0 else "fail"
    return DoctorCheck(cmd, status, detail)


def run_doctor() -> dict[str, Any]:
    checks: list[DoctorCheck] = [
        DoctorCheck("python", "pass", platform.python_version()),
        _probe_module("pydantic"),
        _probe_module("mcp"),
        _probe_command("ruby", "--version"),
        _probe_command("mrbc", "-v"),
        _probe_command("mmdc", "--version"),
        _probe_command("java", "-version"),
        _probe_command("dot", "-V"),
        _probe_command("rubocop", "--version"),
    ]
    jar = os.environ.get("PLANTUML_JAR", "/opt/plantuml/plantuml.jar")
    checks.append(
        DoctorCheck(
            "plantuml",
            "pass" if Path(jar).is_file() else "fail",
            f"jar at {jar}" if Path(jar).is_file() else f"missing jar {jar}",
        )
    )
    failed = [c for c in checks if c.status == "fail"]
    return {
        "verdict": "pass" if not failed else "fail",
        "checks": [
            {"capability": c.capability, "status": c.status, "detail": c.detail} for c in checks
        ],
        "python": sys.version.split()[0],
    }


def main() -> int:
    report = run_doctor()
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] == "pass" else 1
