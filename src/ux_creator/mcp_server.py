"""Expose the ux_creator deterministic entry points over a stdio MCP transport.

Every tool returns a JSON text payload mirroring the CLI verdicts. The
transport never judges the design itself: observations carry no pass
authority beyond what the wrapped function returns.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from . import __version__
from .advisory import (
    load_intake_records,
    load_visual_reviews,
    reconcile_findings,
    reconcile_intake,
)
from .contract import UXContract, load_contract
from .doctor import run_doctor
from .gates import run_gates
from .imports import import_source
from .projections import write_projections, write_provenance
from .proposals import ProposalSet, triage, write_triage
from .render import render_all
from .report import write_report
from .requests import build_request, write_request
from .responses import liaison_status
from .ruby_bridge import contract_from_ruby, mruby_check

server: Server = Server(f"ux-mcp/{__version__}")

_SCHEMAS: dict[str, dict[str, Any]] = {
    "ux_doctor": {"type": "object", "properties": {}, "additionalProperties": False},
    "ux_validate_contract": {
        "type": "object",
        "properties": {"contract": {"type": "object"}},
        "required": ["contract"],
        "additionalProperties": False,
    },
    "ux_gates": {
        "type": "object",
        "properties": {"contract_path": {"type": "string"}, "workspace": {"type": "string"}},
        "required": ["contract_path"],
        "additionalProperties": False,
    },
    "ux_author": {
        "type": "object",
        "properties": {
            "contract_path": {"type": "string"},
            "out_dir": {"type": "string"},
            "render": {"type": "boolean"},
        },
        "required": ["contract_path", "out_dir"],
        "additionalProperties": False,
    },
    "ux_from_ruby": {
        "type": "object",
        "properties": {"source": {"type": "string"}, "out": {"type": "string"}},
        "required": ["source", "out"],
        "additionalProperties": False,
    },
    "ux_import": {
        "type": "object",
        "properties": {
            "contract_path": {"type": "string"},
            "system": {"type": "string", "enum": ["circuit", "mech", "wire", "bard", "csv"]},
            "file": {"type": "string"},
        },
        "required": ["contract_path", "system", "file"],
        "additionalProperties": False,
    },
    "ux_request": {
        "type": "object",
        "properties": {
            "contract_path": {"type": "string"},
            "target_agent": {"type": "string"},
            "risk": {"type": "string", "enum": ["low", "high"]},
            "rationale": {"type": "string"},
            "requested_changes": {"type": "array", "items": {"type": "string"}},
            "out_dir": {"type": "string"},
        },
        "required": ["contract_path", "target_agent", "risk", "requested_changes", "out_dir"],
        "additionalProperties": False,
    },
    "ux_propose": {
        "type": "object",
        "properties": {
            "contract_path": {"type": "string"},
            "proposals_path": {"type": "string"},
            "out_dir": {"type": "string"},
        },
        "required": ["contract_path", "proposals_path", "out_dir"],
        "additionalProperties": False,
    },
    "ux_mruby_check": {
        "type": "object",
        "properties": {"source": {"type": "string"}},
        "required": ["source"],
        "additionalProperties": False,
    },
    "ux_review_reconcile": {
        "type": "object",
        "properties": {
            "contract_path": {"type": "string"},
            "out_dir": {"type": "string"},
            "workspace": {"type": "string"},
        },
        "required": ["contract_path", "out_dir"],
        "additionalProperties": False,
    },
    "ux_liaison_status": {
        "type": "object",
        "properties": {"out_dir": {"type": "string"}},
        "required": ["out_dir"],
        "additionalProperties": False,
    },
    "ux_intake_reconcile": {
        "type": "object",
        "properties": {
            "contract_path": {"type": "string"},
            "out_dir": {"type": "string"},
        },
        "required": ["contract_path", "out_dir"],
        "additionalProperties": False,
    },
    "ux_render": {
        "type": "object",
        "properties": {"dir": {"type": "string"}},
        "required": ["dir"],
        "additionalProperties": False,
    },
}

_WRITE_TOOLS = {"ux_author", "ux_import", "ux_request", "ux_propose", "ux_from_ruby"}


def _text(payload: Any) -> list[types.ContentBlock]:
    return [types.TextContent(type="text", text=json.dumps(payload, indent=2, sort_keys=True))]


def tool_specs() -> list[types.Tool]:
    specs: list[types.Tool] = []
    for name, schema in _SCHEMAS.items():
        specs.append(
            types.Tool(
                name=name,
                description=name.replace("_", " "),
                inputSchema=schema,
                annotations=types.ToolAnnotations(
                    title=name,
                    readOnlyHint=name not in _WRITE_TOOLS,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            )
        )
    return specs


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return tool_specs()


async def dispatch_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "ux_doctor":
        return run_doctor()
    if name == "ux_validate_contract":
        try:
            UXContract.model_validate(arguments["contract"])
        except Exception as exc:
            return {"verdict": "fail", "stage": "validate", "detail": str(exc)}
        return {"verdict": "pass", "stage": "validate"}
    if name == "ux_gates":
        contract = load_contract(arguments["contract_path"])
        report = run_gates(contract, Path(arguments.get("workspace") or "."))
        return report.to_dict(contract)
    if name == "ux_author":
        contract = load_contract(arguments["contract_path"])
        out_dir = Path(arguments["out_dir"])
        name = Path(arguments["contract_path"]).stem.removesuffix(".ux")
        report = run_gates(contract)
        paths = write_projections(contract, name, out_dir)
        renders = render_all(out_dir) if arguments.get("render") else []
        write_provenance(contract, paths, out_dir)
        write_report(contract, report, out_dir, renders)
        return report.to_dict(contract)
    if name == "ux_from_ruby":
        result = contract_from_ruby(Path(arguments["source"]))
        if result.contract is None:
            return {"verdict": "fail", "stage": "from-ruby", "detail": result.detail}
        out = Path(arguments["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(result.contract.model_dump(by_alias=True), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {"verdict": "pass", "stage": "from-ruby", "contract": str(out)}
    if name == "ux_import":
        contract = load_contract(arguments["contract_path"])
        contract = import_source(contract, arguments["system"], Path(arguments["file"]))
        Path(arguments["contract_path"]).write_text(
            json.dumps(contract.model_dump(by_alias=True), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {"verdict": "pass", "imports": [r.model_dump() for r in contract.imports]}
    if name == "ux_request":
        try:
            contract = load_contract(arguments["contract_path"])
            request = build_request(
                contract,
                target_agent=arguments["target_agent"],
                risk=arguments["risk"],
                rationale=arguments.get("rationale", ""),
                requested_changes=arguments["requested_changes"],
            )
            path = write_request(request, Path(arguments["out_dir"]))
        except Exception as exc:
            return {"verdict": "fail", "stage": "request", "detail": str(exc)}
        return {"verdict": "pass", "request": str(path)}
    if name == "ux_propose":
        try:
            contract = load_contract(arguments["contract_path"])
            proposals = ProposalSet.model_validate(
                json.loads(Path(arguments["proposals_path"]).read_text(encoding="utf-8"))
            )
            name_stem = Path(arguments["proposals_path"]).stem.removesuffix(".ux-proposals")
            paths = write_triage(contract, proposals, Path(arguments["out_dir"]), name_stem)
            blocked = [t.id for t in triage(contract, proposals) if t.status != "auto_send"]
        except Exception as exc:
            return {"verdict": "fail", "stage": "propose", "detail": str(exc)}
        return {
            "verdict": "pass",
            "stage": "propose",
            "written": {k: str(p) for k, p in paths.items()},
            "blocked": blocked,
        }
    if name == "ux_mruby_check":
        result = mruby_check(Path(arguments["source"]))
        return {"verdict": "pass" if result.status == "ok" else "fail", "detail": result.detail}
    if name == "ux_review_reconcile":
        try:
            contract = load_contract(arguments["contract_path"])
            report = run_gates(contract, Path(arguments.get("workspace") or "."))
            records, malformed = load_visual_reviews(Path(arguments["out_dir"]))
            findings = reconcile_findings(contract, report, records)
        except Exception as exc:
            return {"verdict": "fail", "stage": "review-reconcile", "detail": str(exc)}
        return {
            "verdict": "pass",
            "stage": "review-reconcile",
            "findings": [f.model_dump() for f in findings],
            "malformed": [str(p) for p in malformed],
        }
    if name == "ux_liaison_status":
        try:
            status = liaison_status(Path(arguments["out_dir"]), Path(arguments["out_dir"]))
        except Exception as exc:
            return {"verdict": "fail", "stage": "liaison", "detail": str(exc)}
        payload = status.model_dump()
        payload["verdict"] = "pass"
        payload["stage"] = "liaison"
        return payload
    if name == "ux_intake_reconcile":
        try:
            contract = load_contract(arguments["contract_path"])
            records, malformed = load_intake_records(Path(arguments["out_dir"]))
            recon = reconcile_intake(contract, records)
            recon.malformed = [str(p) for p in malformed]
        except Exception as exc:
            return {"verdict": "fail", "stage": "intake-reconcile", "detail": str(exc)}
        payload = recon.model_dump()
        payload["verdict"] = "pass"
        payload["stage"] = "intake-reconcile"
        return payload
    if name == "ux_render":
        results = render_all(Path(arguments["dir"]))
        return {
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
    return {"verdict": "fail", "detail": f"unknown tool {name}"}


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.ContentBlock]:
    try:
        payload = await dispatch_tool(name, arguments or {})
    except Exception as exc:  # fail-closed transport
        payload = {"verdict": "fail", "detail": f"{name} error: {exc}"}
    return _text(payload)


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=f"ux-mcp/{__version__}",
                server_version=__version__,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
