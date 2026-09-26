#!/usr/bin/env python3
"""End-to-end authoring driver: contract -> gates -> projections -> report.

Runs inside the digest-pinned ux-tools image (CI) or locally with the
tools on PATH. Exits non-zero unless the gate verdict is "pass"
(fail-closed), so the container exit code is the smoke check.

Usage:
    e2e_authoring.py --contract examples/smart-kettle/smart-kettle.ux.json \
        --out out/smart-kettle [--render]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ux_creator.contract import load_contract  # noqa: E402
from ux_creator.gates import run_gates  # noqa: E402
from ux_creator.projections import write_projections, write_provenance  # noqa: E402
from ux_creator.render import render_all  # noqa: E402
from ux_creator.report import write_report  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)

    contract = load_contract(args.contract)
    name = args.contract.stem.removesuffix(".ux")
    report = run_gates(contract, args.contract.parent)
    paths = write_projections(contract, name, args.out)
    renders = render_all(args.out) if args.render else []
    write_provenance(contract, paths, args.out)
    write_report(contract, report, args.out, renders)
    print(json.dumps({"verdict": report.verdict, "out": str(args.out)}))
    return 0 if report.verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
