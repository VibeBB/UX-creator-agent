"""Expose the ux_creator deterministic entry points over a stdio MCP transport.

Every tool returns a JSON text payload mirroring the CLI verdicts. The
transport never judges the design itself: observations carry no pass
authority beyond what the wrapped function returns.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from pydantic import ValidationError

from . import __version__
from .advisory import (
    load_intake_records,
    load_visual_reviews,
    reconcile_findings,
    reconcile_intake,
)
from .contract import UXContract, load_contract
from .doctor import run_doctor
from .gates import FAIL, PASS, run_gates
from .imports import import_source
from .production import load_plan, plan_sha256, run_production_gates, write_production
from .projections import write_projections, write_provenance
from .proposals import ProposalSet, triage, write_triage
from .records import (
    DecisionInput,
    StageImpressionInput,
    VisionReviewInput,
    record_decision,
    record_impression,
    record_vision_review,
    records_summary,
)
from .render import RenderResult, render_all
from .report import write_report
from .requests import build_request, write_request
from .responses import liaison_status
from .ruby_bridge import contract_from_ruby, mruby_check
from .workspace import workspace_path

server: Server = Server(f"ux-mcp/{__version__}")

_SCHEMAS: dict[str, dict[str, Any]] = {
    "ux_record_decision": DecisionInput.model_json_schema(),
    "ux_record_impression": StageImpressionInput.model_json_schema(),
    "ux_record_vision_review": VisionReviewInput.model_json_schema(),
    "ux_records_status": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
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
    "ux_produce": {
        "type": "object",
        "properties": {
            "plan_path": {"type": "string"},
            "out_dir": {"type": "string"},
            "workspace": {"type": "string"},
            "liaison_dir": {"type": "string"},
        },
        "required": ["plan_path", "out_dir"],
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

_WRITE_TOOLS = {
    "ux_author",
    "ux_import",
    "ux_request",
    "ux_propose",
    "ux_from_ruby",
    "ux_produce",
    "ux_record_decision",
    "ux_record_impression",
    "ux_record_vision_review",
}
_APPEND_RECORD_TOOLS = {
    "ux_record_decision",
    "ux_record_impression",
    "ux_record_vision_review",
}

_IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
_MAX_INLINE_IMAGES = 8
_MAX_INLINE_IMAGE_BYTES = 4 * 1024 * 1024


def _text(payload: Any) -> list[types.ContentBlock]:
    return [types.TextContent(type="text", text=json.dumps(payload, indent=2, sort_keys=True))]


def _path_arg(arguments: dict[str, Any], key: str) -> Path:
    return workspace_path(arguments[key])


def _workspace_arg(arguments: dict[str, Any]) -> Path:
    return workspace_path(arguments.get("workspace") or ".")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as image_file:
        for chunk in iter(lambda: image_file.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _render_content(
    payload: dict[str, Any], renders: list[RenderResult]
) -> list[types.ContentBlock]:
    inline_images: list[dict[str, Any]] = []
    images: list[types.ImageContent] = []
    for render in renders:
        path = render.output
        if render.status != "ok" or path is None:
            continue
        mime = _IMAGE_MIME.get(path.suffix.lower())
        if mime is None:
            continue
        entry: dict[str, Any] = {
            "path": str(path),
            "sha256": None,
            "attached": False,
        }
        if len(images) >= _MAX_INLINE_IMAGES:
            try:
                entry["sha256"] = _file_sha256(path)
            except OSError:
                entry["reason"] = "unavailable"
            else:
                entry["reason"] = "image_limit_reached"
        else:
            try:
                if path.stat().st_size > _MAX_INLINE_IMAGE_BYTES:
                    entry["sha256"] = _file_sha256(path)
                    entry["reason"] = "over_4_mib"
                else:
                    data = path.read_bytes()
                    if len(data) > _MAX_INLINE_IMAGE_BYTES:
                        entry["sha256"] = hashlib.sha256(data).hexdigest()
                        entry["reason"] = "over_4_mib"
                    else:
                        entry["sha256"] = hashlib.sha256(data).hexdigest()
                        entry["attached"] = True
                        images.append(
                            types.ImageContent(
                                type="image",
                                data=base64.b64encode(data).decode("ascii"),
                                mimeType=mime,
                            )
                        )
            except OSError:
                entry["reason"] = "unavailable"
        inline_images.append(entry)
    payload["inline_images"] = inline_images
    return [
        types.TextContent(
            type="text",
            text=json.dumps(payload, indent=2, sort_keys=True),
        ),
        *images,
    ]


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
                    idempotentHint=name not in _APPEND_RECORD_TOOLS,
                    openWorldHint=False,
                ),
            )
        )
    return specs


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return tool_specs()


async def dispatch_tool(
    name: str, arguments: dict[str, Any]
) -> dict[str, Any] | list[types.ContentBlock]:
    if name == "ux_record_decision":
        return record_decision(arguments)
    if name == "ux_record_impression":
        return record_impression(arguments)
    if name == "ux_record_vision_review":
        return record_vision_review(arguments)
    if name == "ux_records_status":
        return records_summary()
    if name == "ux_doctor":
        return run_doctor()
    if name == "ux_validate_contract":
        try:
            UXContract.model_validate(arguments["contract"])
        except (ValidationError, ValueError) as exc:
            return {"verdict": FAIL, "stage": "validate", "detail": str(exc)}
        return {"verdict": PASS, "stage": "validate"}
    if name == "ux_gates":
        contract = load_contract(_path_arg(arguments, "contract_path"))
        report = run_gates(contract, _workspace_arg(arguments))
        return report.to_dict(contract)
    if name == "ux_author":
        contract_path = _path_arg(arguments, "contract_path")
        out_dir = _path_arg(arguments, "out_dir")
        contract = load_contract(contract_path)
        name = contract_path.stem.removesuffix(".ux")
        report = run_gates(contract)
        paths = write_projections(contract, name, out_dir)
        renders = render_all(out_dir, fmts=("svg", "png")) if arguments.get("render") else []
        write_provenance(contract, paths, out_dir)
        write_report(contract, report, out_dir, renders)
        payload = report.to_dict(contract)
        return _render_content(payload, renders) if arguments.get("render") else payload
    if name == "ux_from_ruby":
        result = contract_from_ruby(_path_arg(arguments, "source"))
        if result.contract is None:
            return {"verdict": FAIL, "stage": "from-ruby", "detail": result.detail}
        out = _path_arg(arguments, "out")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(result.contract.model_dump(by_alias=True), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {"verdict": PASS, "stage": "from-ruby", "contract": str(out)}
    if name == "ux_import":
        contract_path = _path_arg(arguments, "contract_path")
        source_path = _path_arg(arguments, "file")
        contract = load_contract(contract_path)
        contract = import_source(contract, arguments["system"], source_path)
        contract_path.write_text(
            json.dumps(contract.model_dump(by_alias=True), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {"verdict": PASS, "imports": [r.model_dump() for r in contract.imports]}
    if name == "ux_request":
        contract_path = _path_arg(arguments, "contract_path")
        out_dir = _path_arg(arguments, "out_dir")
        try:
            contract = load_contract(contract_path)
            request = build_request(
                contract,
                target_agent=arguments["target_agent"],
                risk=arguments["risk"],
                rationale=arguments.get("rationale", ""),
                requested_changes=arguments["requested_changes"],
            )
            path = write_request(request, out_dir)
        except (OSError, ValueError, ValidationError) as exc:
            return {"verdict": FAIL, "stage": "request", "detail": str(exc)}
        return {"verdict": PASS, "request": str(path)}
    if name == "ux_propose":
        contract_path = _path_arg(arguments, "contract_path")
        proposals_path = _path_arg(arguments, "proposals_path")
        out_dir = _path_arg(arguments, "out_dir")
        try:
            contract = load_contract(contract_path)
            proposals = ProposalSet.model_validate(
                json.loads(proposals_path.read_text(encoding="utf-8"))
            )
            name_stem = proposals_path.stem.removesuffix(".ux-proposals")
            paths = write_triage(contract, proposals, out_dir, name_stem)
            blocked = [t.id for t in triage(contract, proposals) if t.status != "auto_send"]
        except (OSError, ValueError, ValidationError) as exc:
            return {"verdict": FAIL, "stage": "propose", "detail": str(exc)}
        return {
            "verdict": PASS,
            "stage": "propose",
            "written": {k: str(p) for k, p in paths.items()},
            "blocked": blocked,
        }
    if name == "ux_mruby_check":
        result = mruby_check(_path_arg(arguments, "source"))
        return {"verdict": PASS if result.status == "ok" else FAIL, "detail": result.detail}
    if name == "ux_review_reconcile":
        contract_path = _path_arg(arguments, "contract_path")
        workspace = _workspace_arg(arguments)
        out_dir = _path_arg(arguments, "out_dir")
        try:
            contract = load_contract(contract_path)
            report = run_gates(contract, workspace)
            records, malformed = load_visual_reviews(out_dir)
            findings = reconcile_findings(contract, report, records)
        except (OSError, ValueError, ValidationError) as exc:
            return {"verdict": FAIL, "stage": "review-reconcile", "detail": str(exc)}
        return {
            "verdict": PASS,
            "stage": "review-reconcile",
            "findings": [f.model_dump() for f in findings],
            "malformed": [str(p) for p in malformed],
        }
    if name == "ux_produce":
        plan_path = _path_arg(arguments, "plan_path")
        workspace = _workspace_arg(arguments)
        liaison = _path_arg(arguments, "liaison_dir") if arguments.get("liaison_dir") else None
        out_dir = _path_arg(arguments, "out_dir")
        try:
            plan = load_plan(plan_path)
            report = run_production_gates(
                plan,
                workspace,
                liaison,
            )
            paths = write_production(
                plan,
                report,
                plan_path.name.removesuffix(".production.json"),
                out_dir,
                plan_path,
            )
        except (OSError, ValueError, ValidationError) as exc:
            return {"verdict": FAIL, "stage": "produce", "detail": str(exc)}
        payload = report.to_dict(plan, plan_sha256(plan_path))
        payload["written"] = {k: str(p) for k, p in sorted(paths.items())}
        return payload
    if name == "ux_liaison_status":
        out_dir = _path_arg(arguments, "out_dir")
        try:
            status = liaison_status(out_dir, out_dir)
        except (OSError, ValueError) as exc:
            return {"verdict": FAIL, "stage": "liaison", "detail": str(exc)}
        payload = status.model_dump()
        payload["verdict"] = PASS
        payload["stage"] = "liaison"
        return payload
    if name == "ux_intake_reconcile":
        contract_path = _path_arg(arguments, "contract_path")
        out_dir = _path_arg(arguments, "out_dir")
        try:
            contract = load_contract(contract_path)
            records, malformed = load_intake_records(out_dir)
            recon = reconcile_intake(contract, records)
            recon.malformed = [str(p) for p in malformed]
        except (OSError, ValueError, ValidationError) as exc:
            return {"verdict": FAIL, "stage": "intake-reconcile", "detail": str(exc)}
        payload = recon.model_dump()
        payload["verdict"] = PASS
        payload["stage"] = "intake-reconcile"
        return payload
    if name == "ux_render":
        results = render_all(_path_arg(arguments, "dir"), fmts=("svg", "png"))
        return _render_content(
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
            },
            results,
        )
    return {"verdict": FAIL, "detail": f"unknown tool {name}"}


@server.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any]
) -> types.CallToolResult | list[types.ContentBlock]:
    if name not in _SCHEMAS:
        return types.CallToolResult(
            content=_text({"verdict": FAIL, "detail": f"unknown tool {name}"}),
            isError=True,
        )
    try:
        payload = await dispatch_tool(name, arguments or {})
    except Exception as exc:
        return types.CallToolResult(
            content=_text(
                {
                    "verdict": FAIL,
                    "detail": f"{name} error: {exc}",
                    "error_type": type(exc).__name__,
                }
            ),
            isError=True,
        )
    return payload if isinstance(payload, list) else _text(payload)


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
