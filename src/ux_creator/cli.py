"""python -m ux_creator — deterministic CLI entry points.

Subcommands: doctor, gates, author, render, import, from-ruby, mruby-check,
request, review-record.

Every subcommand prints a JSON verdict object and exits 0 only on
"pass"/"ok"; fail-closed throughout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .advisory import write_visual_review
from .contract import load_contract
from .doctor import run_doctor
from .gates import run_gates
from .imports import import_source
from .projections import write_projections, write_provenance
from .render import render_all
from .report import write_report
from .requests import build_request, write_request
from .ruby_bridge import contract_from_ruby, mruby_check


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _fail(stage: str, exc: Exception) -> int:
    _print({"verdict": "fail", "stage": stage, "detail": str(exc)})
    return 1


def _cmd_doctor(_args: argparse.Namespace) -> int:
    report = run_doctor()
    _print(report)
    return 0 if report["verdict"] == "pass" else 1


def _cmd_gates(args: argparse.Namespace) -> int:
    try:
        contract = load_contract(args.contract)
    except Exception as exc:
        return _fail("load", exc)
    report = run_gates(contract, Path(args.workspace or "."))
    if args.out:
        from .report import write_report as _write

        _write(contract, report, Path(args.out))
    _print(report.to_dict(contract))
    return 0 if report.verdict == "pass" else 1


def _cmd_author(args: argparse.Namespace) -> int:
    """Full projection pass: gates → projections → renders → report."""
    try:
        contract = load_contract(args.contract)
    except Exception as exc:
        return _fail("load", exc)
    out_dir = Path(args.out)
    name = Path(args.contract).stem.removesuffix(".ux")
    report = run_gates(contract, Path(args.workspace or "."))
    paths = write_projections(contract, name, out_dir)
    renders = render_all(out_dir) if args.render else []
    write_provenance(contract, paths, out_dir)
    write_report(contract, report, out_dir, renders)
    _print(report.to_dict(contract))
    return 0 if report.verdict == "pass" else 1


def _cmd_render(args: argparse.Namespace) -> int:
    results = render_all(Path(args.dir))
    _print(
        {
            "verdict": "pass",
            "renders": [
                {
                    "source": str(r.source),
                    "output": str(r.output) if r.output else None,
                    "status": r.status,
                    "detail": r.detail,
                }
                for r in results
            ],
        }
    )
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    try:
        contract = load_contract(args.contract)
        contract = import_source(contract, args.system, Path(args.file))
    except Exception as exc:
        return _fail("import", exc)
    Path(args.contract).write_text(
        json.dumps(contract.model_dump(by_alias=True), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _print(
        {
            "verdict": "pass",
            "stage": "import",
            "imports": [r.model_dump(by_alias=True) for r in contract.imports],
        }
    )
    return 0


def _cmd_from_ruby(args: argparse.Namespace) -> int:
    result = contract_from_ruby(Path(args.source))
    if result.contract is None:
        _print({"verdict": "fail", "stage": "from-ruby", "detail": result.detail})
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result.contract.model_dump(by_alias=True), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _print({"verdict": "pass", "stage": "from-ruby", "contract": str(out)})
    return 0


def _cmd_mruby_check(args: argparse.Namespace) -> int:
    result = mruby_check(Path(args.source))
    _print(
        {
            "verdict": "pass" if result.status == "ok" else "fail",
            "stage": "mruby-check",
            "detail": result.detail,
        }
    )
    return 0 if result.status == "ok" else 1


def _cmd_request(args: argparse.Namespace) -> int:
    try:
        contract = load_contract(args.contract)
        request = build_request(
            contract,
            target_agent=args.target,
            risk=args.risk,
            rationale=args.rationale,
            requested_changes=args.change,
        )
        path = write_request(request, Path(args.out_dir), args.name)
    except Exception as exc:
        return _fail("request", exc)
    _print({"verdict": "pass", "stage": "request", "request": str(path)})
    return 0


def _cmd_review_record(args: argparse.Namespace) -> int:
    try:
        path = write_visual_review(
            Path(args.image),
            args.checklist,
            args.summary,
            [],
            model=args.model,
        )
    except Exception as exc:
        return _fail("review-record", exc)
    _print({"verdict": "pass", "stage": "review-record", "record": str(path)})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ux_creator", description=__doc__)
    parser.add_argument("--version", action="version", version=f"ux-creator {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="probe the tool environment")
    p.add_argument("--warn", action="store_true", help="report but always exit 0")
    p.set_defaults(func=_cmd_doctor)

    p = sub.add_parser("gates", help="run deterministic gates on a contract")
    p.add_argument("contract")
    p.add_argument("--out")
    p.add_argument("--workspace")
    p.set_defaults(func=_cmd_gates)

    p = sub.add_parser("author", help="gates + projections + report")
    p.add_argument("contract")
    p.add_argument("--out", required=True)
    p.add_argument("--workspace")
    p.add_argument("--render", action="store_true")
    p.set_defaults(func=_cmd_author)

    p = sub.add_parser("render", help="render all *.mmd/*.puml under a directory")
    p.add_argument("dir")
    p.set_defaults(func=_cmd_render)

    p = sub.add_parser("import", help="import a sibling contract file")
    p.add_argument("contract")
    p.add_argument(
        "--from", dest="system", required=True, choices=["circuit", "mech", "wire", "bard", "csv"]
    )
    p.add_argument("file")
    p.set_defaults(func=_cmd_import)

    p = sub.add_parser("from-ruby", help="compile a .ux.rb DSL file to .ux.json")
    p.add_argument("source")
    p.add_argument("--out", required=True)
    p.set_defaults(func=_cmd_from_ruby)

    p = sub.add_parser("mruby-check", help="mrbc -c syntax check on a Ruby snippet")
    p.add_argument("source")
    p.set_defaults(func=_cmd_mruby_check)

    p = sub.add_parser("request", help="write a ux-request.json for a sibling agent")
    p.add_argument("contract")
    p.add_argument("--target", required=True)
    p.add_argument("--risk", required=True, choices=["low", "high"])
    p.add_argument("--rationale", default="")
    p.add_argument("--change", action="append", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--name", default="ux-request")
    p.set_defaults(func=_cmd_request)

    p = sub.add_parser("review-record", help="write a review-visual advisory record")
    p.add_argument("image")
    p.add_argument(
        "--checklist",
        required=True,
        choices=["journey_map", "statechart", "wireframe", "intake_image"],
    )
    p.add_argument("--summary", required=True)
    p.add_argument("--model", default="")
    p.set_defaults(func=_cmd_review_record)

    args = parser.parse_args(argv)
    if args.command == "doctor" and getattr(args, "warn", False):
        report = run_doctor()
        _print(report)
        return 0
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
