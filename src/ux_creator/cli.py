"""python -m ux_creator — deterministic CLI entry points.

Subcommands: doctor, gates, author, render, import, from-ruby, mruby-check,
request, propose, review-record, review-reconcile, liaison, produce,
intake-record, intake-reconcile, record.

Every subcommand prints a JSON verdict object and exits 0 only on
"pass"/"ok"; fail-closed throughout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError

from . import __version__
from .advisory import (
    TouchpointCandidate,
    VisualFinding,
    load_intake_records,
    load_visual_reviews,
    reconcile_findings,
    reconcile_intake,
    write_intake_record,
    write_visual_review,
    write_visual_review_not_applicable,
)
from .contract import load_contract
from .doctor import run_doctor
from .gates import FAIL, PASS, run_gates
from .imports import import_source
from .production import load_plan, plan_sha256, run_production_gates, write_production
from .projections import write_projections, write_provenance
from .proposals import ProposalSet, triage, write_triage
from .records import RECORDERS, record_vision_review, records_summary
from .render import render_all
from .report import write_report
from .requests import build_request, write_request
from .responses import liaison_status
from .ruby_bridge import contract_from_ruby, mruby_check
from .workspace import workspace_path, workspace_root


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _fail(stage: str, exc: Exception) -> int:
    _print({"verdict": FAIL, "stage": stage, "detail": str(exc)})
    return 1


def _cmd_doctor(_args: argparse.Namespace) -> int:
    report = run_doctor()
    _print(report)
    return 0 if report["verdict"] == PASS else 1


def _cmd_gates(args: argparse.Namespace) -> int:
    try:
        contract = load_contract(args.contract)
    except (OSError, ValueError, ValidationError) as exc:
        return _fail("load", exc)
    report = run_gates(contract, Path(args.workspace or "."))
    if args.out:
        from .report import write_report as _write

        _write(contract, report, Path(args.out))
    _print(report.to_dict(contract))
    return 0 if report.verdict == PASS else 1


def _cmd_author(args: argparse.Namespace) -> int:
    """Full projection pass: gates → projections → renders → report."""
    try:
        contract = load_contract(args.contract)
    except (OSError, ValueError, ValidationError) as exc:
        return _fail("load", exc)
    out_dir = Path(args.out)
    name = Path(args.contract).stem.removesuffix(".ux")
    report = run_gates(contract, Path(args.workspace or "."))
    paths = write_projections(contract, name, out_dir)
    renders = render_all(out_dir, fmts=("svg", "png")) if args.render else []
    write_provenance(contract, paths, out_dir)
    write_report(contract, report, out_dir, renders)
    _print(report.to_dict(contract))
    return 0 if report.verdict == PASS else 1


def _cmd_render(args: argparse.Namespace) -> int:
    results = render_all(Path(args.dir), fmts=("svg", "png"))
    _print(
        {
            "verdict": PASS,
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
    except (OSError, ValueError, ValidationError) as exc:
        return _fail("import", exc)
    Path(args.contract).write_text(
        json.dumps(contract.model_dump(by_alias=True), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _print(
        {
            "verdict": PASS,
            "stage": "import",
            "imports": [r.model_dump(by_alias=True) for r in contract.imports],
        }
    )
    return 0


def _cmd_from_ruby(args: argparse.Namespace) -> int:
    result = contract_from_ruby(Path(args.source))
    if result.contract is None:
        _print({"verdict": FAIL, "stage": "from-ruby", "detail": result.detail})
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result.contract.model_dump(by_alias=True), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _print({"verdict": PASS, "stage": "from-ruby", "contract": str(out)})
    return 0


def _cmd_mruby_check(args: argparse.Namespace) -> int:
    result = mruby_check(Path(args.source))
    _print(
        {
            "verdict": PASS if result.status == "ok" else FAIL,
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
    except (OSError, ValueError, ValidationError) as exc:
        return _fail("request", exc)
    _print({"verdict": PASS, "stage": "request", "request": str(path)})
    return 0


def _cmd_propose(args: argparse.Namespace) -> int:
    try:
        contract = load_contract(args.contract)
        proposals = ProposalSet.model_validate(
            json.loads(Path(args.proposals).read_text(encoding="utf-8"))
        )
        name = Path(args.proposals).stem.removesuffix(".ux-proposals")
        paths = write_triage(contract, proposals, Path(args.out_dir), name)
        blocked = [t.id for t in triage(contract, proposals) if t.status != "auto_send"]
    except (OSError, ValueError, ValidationError) as exc:
        return _fail("propose", exc)
    _print(
        {
            "verdict": PASS,
            "stage": "propose",
            "written": {k: str(p) for k, p in paths.items()},
            "blocked": blocked,
        }
    )
    return 0


def _cmd_intake_record(args: argparse.Namespace) -> int:
    try:
        candidates: list[TouchpointCandidate] = []
        for spec in cast("list[str]", args.touchpoint):
            head, _, evidence = spec.partition("=")
            cid, _, surface = head.partition("@")
            if not cid or not evidence:
                raise ValueError(f"--touchpoint expects ID[@SURFACE]=EVIDENCE, got {spec!r}")
            candidates.append(
                TouchpointCandidate(
                    id=cid,
                    surface=surface,
                    evidence=evidence,
                    confidence=args.confidence,
                )
            )
        path = write_intake_record(Path(args.image), candidates, model=args.model)
    except (OSError, ValueError, ValidationError) as exc:
        return _fail("intake-record", exc)
    _print({"verdict": PASS, "stage": "intake-record", "record": str(path)})
    return 0


def _cmd_intake_reconcile(args: argparse.Namespace) -> int:
    try:
        contract = load_contract(args.contract)
        records, malformed = load_intake_records(Path(args.out_dir))
        recon = reconcile_intake(contract, records)
        recon.malformed = [str(p) for p in malformed]
    except (OSError, ValueError, ValidationError) as exc:
        return _fail("intake-reconcile", exc)
    payload = recon.model_dump()
    payload["verdict"] = PASS
    payload["stage"] = "intake-reconcile"
    _print(payload)
    return 0


def _cmd_liaison(args: argparse.Namespace) -> int:
    try:
        status = liaison_status(Path(args.out_dir), Path(args.out_dir))
    except (OSError, ValueError) as exc:
        return _fail("liaison", exc)
    payload = status.model_dump()
    payload["verdict"] = PASS
    payload["stage"] = "liaison"
    _print(payload)
    return 0


def _cmd_record(args: argparse.Namespace) -> int:
    if args.kind == "status":
        _print(records_summary())
        return 0
    try:
        payload: Any = json.loads(Path(args.json).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("record JSON must be an object")
        result = RECORDERS[args.kind](cast(dict[str, Any], payload))
    except (OSError, ValueError, ValidationError) as exc:
        return _fail("record", exc)
    _print(result)
    return 0 if result.get("verdict") == PASS else 1


def _cmd_produce(args: argparse.Namespace) -> int:
    """Product-level plan: production gates → status projections."""
    try:
        plan_path = Path(args.plan)
        plan = load_plan(plan_path)
        workspace = Path(args.workspace or ".")
        liaison_dir = Path(args.liaison_dir) if args.liaison_dir else None
        report = run_production_gates(plan, workspace, liaison_dir)
        name = plan_path.name.removesuffix(".production.json")
        paths = write_production(plan, report, name, Path(args.out), plan_path)
        renders = render_all(Path(args.out), fmts=("svg", "png")) if args.render else []
    except (OSError, ValueError, ValidationError) as exc:
        return _fail("produce", exc)
    payload = report.to_dict(plan, plan_sha256(plan_path))
    payload["written"] = {k: str(p) for k, p in sorted(paths.items())}
    if args.render:
        payload["renders"] = [
            {
                "source": str(render.source),
                "output": str(render.output) if render.output else None,
                "status": render.status,
                "detail": render.detail,
            }
            for render in renders
        ]
    _print(payload)
    return 0 if report.verdict == PASS else 1


def _cmd_review_reconcile(args: argparse.Namespace) -> int:
    try:
        contract = load_contract(args.contract)
        report = run_gates(contract, Path(args.workspace or "."))
        records, malformed = load_visual_reviews(Path(args.out_dir))
        findings = reconcile_findings(contract, report, records)
    except (OSError, ValueError, ValidationError) as exc:
        return _fail("review-reconcile", exc)
    _print(
        {
            "verdict": PASS,
            "stage": "review-reconcile",
            "findings": [f.model_dump() for f in findings],
            "malformed": [str(p) for p in malformed],
        }
    )
    return 0


def _cmd_review_record(args: argparse.Namespace) -> int:
    try:
        root = workspace_root()
        image = workspace_path(args.image, root)
        if args.not_applicable:
            if args.finding:
                raise ValueError("--finding cannot be used when the visual review is not applicable")
            path = write_visual_review_not_applicable(
                image, args.checklist, args.summary
            )
            _print(
                {
                    "verdict": PASS,
                    "stage": "review-record",
                    "status": "not_applicable",
                    "record": str(path),
                }
            )
            return 0
        findings = [_parse_review_finding(spec) for spec in args.finding]
        model = args.model.strip() or "unspecified"
        severity_map = {"info": "info", "minor": "warning", "major": "error"}
        record = record_vision_review(
            {
                "image_path": image.relative_to(root).as_posix(),
                "model": model,
                "checklist": args.checklist.replace("_", "-"),
                "findings": [
                    {
                        "category": finding.category,
                        "severity": severity_map[finding.severity],
                        "note": (
                            f"{finding.observation} @ {finding.where}"
                            if finding.where
                            else finding.observation
                        ),
                    }
                    for finding in findings
                ],
                "impression": args.summary,
            },
            root=root,
        )
        path = write_visual_review(image, args.checklist, args.summary, findings, model=model)
    except (OSError, ValueError, ValidationError) as exc:
        return _fail("review-record", exc)
    _print(
        {
            "verdict": PASS,
            "stage": "review-record",
            "record": str(path),
            "vision_record": record["path"],
        }
    )
    return 0


def _parse_review_finding(value: str) -> VisualFinding:
    category, first_sep, remaining = value.partition(":")
    severity, second_sep, remaining = remaining.partition(":")
    where, third_sep, observation = remaining.partition(":")
    if not first_sep or not second_sep or not third_sep:
        raise ValueError(
            "--finding expects CATEGORY:SEVERITY:WHERE:OBSERVATION, "
            f"got {value!r}"
        )
    return VisualFinding(
        category=category,
        severity=severity,
        where=where,
        observation=observation,
    )


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

    p = sub.add_parser("propose", help="QCD-triage a ux-proposals.json into ux-requests")
    p.add_argument("--contract", required=True)
    p.add_argument("--proposals", required=True)
    p.add_argument("--out-dir", required=True)
    p.set_defaults(func=_cmd_propose)

    p = sub.add_parser("review-record", help="write a review-visual advisory record")
    p.add_argument("image")
    p.add_argument(
        "--checklist",
        required=True,
        choices=[
            "journey_map",
            "statechart",
            "wireframe",
            "intake_image",
            "service_blueprint",
            "emotion_curve",
            "production_plan",
            "sister_artifact",
        ],
    )
    p.add_argument("--summary", required=True)
    p.add_argument("--model", default="")
    p.add_argument(
        "--not-applicable",
        action="store_true",
        help="record that the image did not reach a vision-capable model",
    )
    p.add_argument(
        "--finding",
        action="append",
        default=[],
        help="CATEGORY:SEVERITY:WHERE:OBSERVATION (repeatable)",
    )
    p.set_defaults(func=_cmd_review_record)

    p = sub.add_parser(
        "review-reconcile", help="reconcile review-visual advisory findings with gates"
    )
    p.add_argument("--contract", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--workspace")
    p.set_defaults(func=_cmd_review_reconcile)

    p = sub.add_parser("liaison", help="report ux-request/ux-response liaison status")
    p.add_argument("--out-dir", required=True)
    p.set_defaults(func=_cmd_liaison)

    p = sub.add_parser("produce", help="product-level plan gates + production status")
    p.add_argument("plan", help="<product>.production.json")
    p.add_argument("--out", required=True)
    p.add_argument("--workspace", default=None)
    p.add_argument("--liaison-dir", default=None, help="dir holding ux-request/ux-response files")
    p.add_argument("--render", action="store_true", help="render the production Mermaid plan")
    p.set_defaults(func=_cmd_produce)

    p = sub.add_parser("intake-record", help="write an intake-touchpoints advisory record")
    p.add_argument("image")
    p.add_argument(
        "--touchpoint",
        action="append",
        required=True,
        help="ID[@SURFACE]=EVIDENCE (repeatable)",
    )
    p.add_argument("--confidence", default="medium", choices=["low", "medium", "high"])
    p.add_argument("--model", default="")
    p.set_defaults(func=_cmd_intake_record)

    p = sub.add_parser("intake-reconcile", help="reconcile intake records against the contract")
    p.add_argument("--contract", required=True)
    p.add_argument("--out-dir", required=True)
    p.set_defaults(func=_cmd_intake_reconcile)

    p = sub.add_parser("record", help="append a VibeBB Record Protocol record")
    p.add_argument("kind", choices=["decision", "impression", "vision-review", "status"])
    p.add_argument("--json", default=None, help="JSON object file with the record fields")

    args = parser.parse_args(argv)
    if args.command == "record" and args.kind != "status" and not args.json:
        parser.error("record decision|impression|vision-review requires --json")
    try:
        if args.command == "doctor" and getattr(args, "warn", False):
            report = run_doctor()
            _print(report)
            return 0
        return int(args.func(args))
    except Exception as exc:
        _print(
            {
                "verdict": FAIL,
                "stage": args.command,
                "detail": str(exc),
                "error_type": type(exc).__name__,
            }
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
