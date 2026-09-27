#!/usr/bin/env python3
"""Ruby DSL parity and lint checks — run inside the ux-tools image.

Verifies that `ruby ruby/bin/ux-dsl` reproduces the committed
`examples/smart-kettle/smart-kettle.ux.json` byte-for-byte, that
`ruby -w` is warning-clean on the library and runner, that the minitest
suite passes, and that rubocop accepts `ruby/`. Missing ruby/rubocop is a
hard failure here — this script is only expected to run where the
toolchain exists (the pinned image).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DSL = ROOT / "ruby" / "bin" / "ux-dsl"
EXAMPLE_RB = ROOT / "examples" / "smart-kettle" / "smart-kettle.ux.rb"
EXAMPLE_JSON = ROOT / "examples" / "smart-kettle" / "smart-kettle.ux.json"


def _run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False, **kwargs)  # type: ignore[arg-type]


def main() -> int:
    failures: list[str] = []

    proc = _run(["ruby", str(DSL), str(EXAMPLE_RB)])
    if proc.returncode != 0:
        failures.append(f"ux-dsl failed: {proc.stderr.strip()}")
    elif proc.stdout != EXAMPLE_JSON.read_text(encoding="utf-8"):
        failures.append("ux-dsl output != committed smart-kettle.ux.json")

    for target in (ROOT / "ruby" / "lib" / "ux_dsl.rb", DSL):
        proc = _run(["ruby", "-w", "-c", str(target)])
        if proc.returncode != 0 or "Syntax OK" not in proc.stdout:
            failures.append(f"ruby -w -c {target.name}: {proc.stdout}{proc.stderr}")

    proc = _run(
        ["ruby", "-I", str(ROOT / "ruby" / "lib"), str(ROOT / "ruby" / "test" / "ux_dsl_test.rb")]
    )
    if proc.returncode != 0:
        failures.append(f"minitest failed: {(proc.stdout + proc.stderr)[-500:]}")

    proc = _run(["rubocop", "--config", str(ROOT / "ruby" / ".rubocop.yml"), str(ROOT / "ruby")])
    if proc.returncode != 0:
        failures.append(f"rubocop failed: {(proc.stdout + proc.stderr)[-500:]}")

    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ruby DSL checks passed: dsl parity, ruby -w, minitest, rubocop")
    return 0


if __name__ == "__main__":
    sys.exit(main())
