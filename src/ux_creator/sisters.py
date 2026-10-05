"""Registry of VibeBB sister plugins and their UX liaison agents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

TARGET_AGENTS = (
    "bard",
    "circuit",
    "dashboard",
    "doc",
    "firmware",
    "fpga",
    "mech",
    "prodeng",
    "sim",
    "wire",
)
TargetAgent = Literal[
    "bard",
    "circuit",
    "dashboard",
    "doc",
    "firmware",
    "fpga",
    "mech",
    "prodeng",
    "sim",
    "wire",
]

PRODUCT_STAGES = (
    "requirements",
    "design",
    "manufacturing_handoff",
    "build",
    "evaluation",
    "revision",
)
ProductStage = Literal[
    "requirements",
    "design",
    "manufacturing_handoff",
    "build",
    "evaluation",
    "revision",
]

SLUG: Final = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
SHA256: Final = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Sister:
    name: str
    repo: str
    agents: tuple[str, ...]
    liaison_agent: str
    inbox_tool: str
    respond_tool: str
    record_decision_tool: str
    record_impression_tool: str
    delivers: str


SISTERS: Final[dict[str, Sister]] = {
    "bard": Sister(
        "bard",
        "bard-agent",
        ("bard", "bard-cue", "bard-critic"),
        "bard",
        "bard_ux_inbox",
        "bard_ux_respond",
        "bard_record_decision",
        "bard_record_impression",
        "sound cues and music",
    ),
    "circuit": Sister(
        "circuit",
        "electrical-circuit-agent",
        (
            "circuit-brief",
            "circuit-schematic",
            "circuit-layout",
            "circuit-library",
            "circuit-review",
            "circuit-part-author-a",
            "circuit-part-author-b",
        ),
        "circuit-brief",
        "circuit_ux_inbox",
        "circuit_ux_respond",
        "circuit_record_decision",
        "circuit_record_impression",
        "electrical design",
    ),
    "dashboard": Sister(
        "dashboard",
        "dashboard-agent",
        ("dashboard-architect", "dashboard-developer", "dashboard-review"),
        "dashboard-architect",
        "dashboard_ux_inbox",
        "dashboard_ux_respond",
        "dashboard_record_decision",
        "dashboard_record_impression",
        "operator and telemetry UI",
    ),
    "doc": Sister(
        "doc",
        "document-agent",
        ("doc-liaison", "doc-writer", "doc-review", "doc-launch"),
        "doc-liaison",
        "doc_ux_inbox",
        "doc_ux_respond",
        "doc_record_decision",
        "doc_record_impression",
        "user and maintainer documentation",
    ),
    "firmware": Sister(
        "firmware",
        "firmware-agent",
        ("firmware-architect", "firmware-developer", "firmware-review"),
        "firmware-architect",
        "firmware_ux_inbox",
        "firmware_ux_respond",
        "firmware_record_decision",
        "firmware_record_impression",
        "embedded software",
    ),
    "fpga": Sister(
        "fpga",
        "fpga-agent",
        ("fpga-architect", "fpga-developer", "fpga-review"),
        "fpga-architect",
        "fpga_ux_inbox",
        "fpga_ux_respond",
        "fpga_record_decision",
        "fpga_record_impression",
        "programmable logic",
    ),
    "mech": Sister(
        "mech",
        "mechanical-agent",
        ("mech-brief", "mech-design", "mech-review"),
        "mech-brief",
        "mech_ux_inbox",
        "mech_ux_respond",
        "mech_record_decision",
        "mech_record_impression",
        "enclosure and mechanical design",
    ),
    "prodeng": Sister(
        "prodeng",
        "production-engineering-agent",
        ("prodeng-liaison", "prodeng-planner", "prodeng-ftm", "prodeng-review"),
        "prodeng-liaison",
        "prodeng_ux_inbox",
        "prodeng_ux_respond",
        "prodeng_record_decision",
        "prodeng_record_impression",
        "manufacturing and production engineering",
    ),
    "sim": Sister(
        "sim",
        "simulation-agent",
        ("sim-liaison", "sim-analyst", "sim-review"),
        "sim-liaison",
        "sim_ux_inbox",
        "sim_ux_respond",
        "sim_record_decision",
        "sim_record_impression",
        "simulation and analysis",
    ),
    "wire": Sister(
        "wire",
        "wire-agent",
        ("wire-brief", "wire-design", "wire-review"),
        "wire-brief",
        "wire_ux_inbox",
        "wire_ux_respond",
        "wire_record_decision",
        "wire_record_impression",
        "electrical wiring and harnesses",
    ),
}
