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
    delivers: str


SISTERS: Final[dict[str, Sister]] = {
    "bard": Sister(
        "bard",
        "bard-agent",
        ("bard", "bard-cue", "bard-critic"),
        "bard",
        "bard_ux_inbox",
        "bard_ux_respond",
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
        "electrical design",
    ),
    "dashboard": Sister(
        "dashboard",
        "dashboard-agent",
        ("dashboard-architect", "dashboard-developer", "dashboard-review"),
        "dashboard-architect",
        "dashboard_ux_inbox",
        "dashboard_ux_respond",
        "operator and telemetry UI",
    ),
    "doc": Sister(
        "doc",
        "document-agent",
        ("doc-liaison", "doc-writer", "doc-review", "doc-launch"),
        "doc-liaison",
        "doc_ux_inbox",
        "doc_ux_respond",
        "user and maintainer documentation",
    ),
    "firmware": Sister(
        "firmware",
        "firmware-agent",
        ("firmware-architect", "firmware-developer", "firmware-review"),
        "firmware-architect",
        "firmware_ux_inbox",
        "firmware_ux_respond",
        "embedded software",
    ),
    "fpga": Sister(
        "fpga",
        "fpga-agent",
        ("fpga-architect", "fpga-developer", "fpga-review"),
        "fpga-architect",
        "fpga_ux_inbox",
        "fpga_ux_respond",
        "programmable logic",
    ),
    "mech": Sister(
        "mech",
        "mechanical-agent",
        ("mech-brief", "mech-design", "mech-review"),
        "mech-brief",
        "mech_ux_inbox",
        "mech_ux_respond",
        "enclosure and mechanical design",
    ),
    "prodeng": Sister(
        "prodeng",
        "production-engineering-agent",
        ("prodeng-liaison", "prodeng-planner", "prodeng-ftm", "prodeng-review"),
        "prodeng-liaison",
        "prodeng_ux_inbox",
        "prodeng_ux_respond",
        "manufacturing and production engineering",
    ),
    "sim": Sister(
        "sim",
        "simulation-agent",
        ("sim-liaison", "sim-analyst", "sim-review"),
        "sim-liaison",
        "sim_ux_inbox",
        "sim_ux_respond",
        "simulation and analysis",
    ),
    "wire": Sister(
        "wire",
        "wire-agent",
        ("wire-brief", "wire-design", "wire-review"),
        "wire-brief",
        "wire_ux_inbox",
        "wire_ux_respond",
        "electrical wiring and harnesses",
    ),
}
