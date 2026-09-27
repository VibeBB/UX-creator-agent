"""Ruby subprocess adapter.

`ruby` is an unmodified external runtime: `ruby/bin/ux-dsl file.rb` prints
the `.ux.json` contract to stdout, and this module validates it into the
UXContract model. Missing ruby or a failing DSL run is fail-closed — the
caller reports `unknown`/raises rather than guessing.

`mruby-check` runs `mrbc -c` on a snippet for embedded-firmware UX logic.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .contract import UXContract

_DSL_RUNNER = Path(__file__).resolve().parents[2] / "ruby" / "bin" / "ux-dsl"


@dataclass(frozen=True)
class BridgeResult:
    status: str  # "ok" | "unknown"
    detail: str
    contract: UXContract | None = None


def _find_runner() -> Path | None:
    candidates = [
        _DSL_RUNNER,
        Path.cwd() / "ruby" / "bin" / "ux-dsl",
        Path("/opt/ux/ruby/bin/ux-dsl"),
    ]
    return next((c for c in candidates if c.is_file()), None)


def contract_from_ruby(source: Path, timeout: int = 60) -> BridgeResult:
    ruby = shutil.which("ruby")
    if ruby is None:
        return BridgeResult("unknown", "ruby not on PATH")
    runner = _find_runner()
    if runner is None:
        return BridgeResult("unknown", "ruby/bin/ux-dsl runner not found")
    proc = subprocess.run(
        [ruby, str(runner), str(source)],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        return BridgeResult("unknown", proc.stderr.strip() or "ux-dsl failed")
    try:
        contract = UXContract.model_validate(json.loads(proc.stdout))
    except (json.JSONDecodeError, ValueError) as exc:
        return BridgeResult("unknown", f"invalid contract from DSL: {exc}")
    return BridgeResult("ok", "", contract)


def mruby_check(source: Path, timeout: int = 30) -> BridgeResult:
    mrbc = shutil.which("mrbc")
    if mrbc is None:
        return BridgeResult("unknown", "mrbc not on PATH (mruby toolchain missing)")
    proc = subprocess.run(
        [mrbc, "-c", str(source)], capture_output=True, text=True, timeout=timeout, check=False
    )
    if proc.returncode != 0:
        return BridgeResult("unknown", proc.stderr.strip() or "mrbc -c failed")
    return BridgeResult("ok", proc.stdout.strip())
