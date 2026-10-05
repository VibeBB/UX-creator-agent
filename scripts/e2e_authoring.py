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
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ux_creator.contract import load_contract  # noqa: E402
from ux_creator.gates import run_gates  # noqa: E402
from ux_creator.projections import write_projections, write_provenance  # noqa: E402
from ux_creator.proposals import ProposalSet, triage, write_triage  # noqa: E402
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
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    workspace_contract = out_dir / _contract_relative_path(args.contract)
    workspace_contract.parent.mkdir(parents=True, exist_ok=True)
    _copy_if_distinct(args.contract, workspace_contract)
    for pattern in ("*.ux-request.json", "*.ux-response.json"):
        for record in sorted(args.contract.parent.glob(pattern)):
            _copy_if_distinct(record, out_dir / record.name)
    for intake in args.contract.parent.glob("intake-touchpoints-*.advisory.json"):
        _copy_if_distinct(intake, out_dir / intake.name)
    report = run_gates(contract, args.contract.parent)
    paths = write_projections(contract, name, out_dir)
    renders = render_all(out_dir) if args.render else []
    write_provenance(contract, paths, out_dir)

    proposals_path = args.contract.with_name(
        args.contract.stem.removesuffix(".ux") + ".ux-proposals.json"
    )
    if proposals_path.exists():
        proposals = ProposalSet.model_validate(
            json.loads(proposals_path.read_text(encoding="utf-8"))
        )
        name = proposals_path.stem.removesuffix(".ux-proposals")
        triage_paths = write_triage(
            contract,
            proposals,
            out_dir / "proposal-triage",
            name,
            contract_path=workspace_contract,
            workspace=out_dir,
        )
        _copy_if_distinct(triage_paths["triage"], out_dir / triage_paths["triage"].name)
        blocked = [t.id for t in triage(contract, proposals) if t.status != "auto_send"]
        print(json.dumps({"stage": "propose", "blocked": blocked}))

    write_report(contract, report, out_dir, renders)
    print(json.dumps({"verdict": report.verdict, "out": str(out_dir)}))
    return 0 if report.verdict == "pass" else 1


def _contract_relative_path(contract_path: Path) -> Path:
    try:
        return contract_path.resolve().relative_to(ROOT)
    except ValueError:
        return Path("examples") / contract_path.parent.name / contract_path.name


def _copy_if_distinct(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)


if __name__ == "__main__":
    sys.exit(main())
