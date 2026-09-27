"""UXContract — the single data model and authority for UX design.

A ``<project>.ux.json`` file captures personas, jobs-to-be-done (ODI),
customer journeys, a service blueprint, statecharts, surfaces, the core
experience, the QCD stance, and provenance for imported sibling artifacts.
Everything downstream (gates, projections, reports) is a deterministic
projection of this model; the file is truth, never the outputs.

The same schema is emitted by the Ruby DSL (`ruby/bin/ux-dsl`) and by
`python -m ux_creator from-ruby`; both validate into `UXContract`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 1
SYSTEM = "ux-creator"

SurfaceLayer = Literal[
    "hardware",
    "mechanism",
    "industrial_design",
    "circuit",
    "firmware",
    "cloud_backend",
    "web_ui",
    "smartphone_app",
    "pc_app",
]

QCDLevel = Literal["low", "medium", "high"]
QCDDelivery = Literal["slow", "normal", "fast"]
RiskLevel = Literal["low", "high"]
StageKind = Literal["discover", "onboard", "use", "recover", "exit"]
FeedbackModality = Literal["visual", "audio", "haptic", "motion", "text"]
LoopCadence = Literal["moment", "session", "daily", "weekly"]

LAYERS: tuple[SurfaceLayer, ...] = (
    "hardware",
    "mechanism",
    "industrial_design",
    "circuit",
    "firmware",
    "cloud_backend",
    "web_ui",
    "smartphone_app",
    "pc_app",
)


class Surface(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    layer: SurfaceLayer
    name: str = ""
    notes: str = ""


class Persona(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = ""
    goals: list[str] = Field(default_factory=list[str])
    context: str = ""
    pains: list[str] = Field(default_factory=list[str])


class Job(BaseModel):
    """A JTBD job with ODI importance/satisfaction scores (1-10)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    functional: str = Field(min_length=1)
    emotional: str = ""
    social: str = ""
    importance: int = Field(ge=1, le=10)
    satisfaction: int = Field(ge=1, le=10)

    @property
    def opportunity(self) -> float:
        """ODI opportunity score: importance + max(importance - satisfaction, 0)."""
        return self.importance + max(self.importance - self.satisfaction, 0)

    @property
    def served(self) -> Literal["underserved", "appropriate", "overserved"]:
        """ODI classification: >=15 underserved, <=10 overserved, else appropriate."""
        if self.opportunity >= 15:
            return "underserved"
        if self.opportunity <= 10:
            return "overserved"
        return "appropriate"


class Stage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    kind: StageKind = "use"
    touchpoints: list[str] = Field(default_factory=list[str])
    emotion: int = Field(ge=1, le=5)
    pain_points: list[str] = Field(default_factory=list[str])
    surfaces: list[str] = Field(default_factory=list[str])
    jobs: list[str] = Field(default_factory=list[str])


class Journey(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    persona: str = ""
    stages: list[Stage] = Field(min_length=1)


class ServiceBlueprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frontstage: list[str] = Field(default_factory=list[str])
    backstage: list[str] = Field(default_factory=list[str])
    support_processes: list[str] = Field(default_factory=list[str])


class StateDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    initial: bool = False
    final: bool = False
    description: str = ""
    surface: str = ""  # surface id the state renders on; "" = none
    entry: list[str] = Field(default_factory=list[str])
    exit: list[str] = Field(default_factory=list[str])


class Transition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_state: str = Field(min_length=1, alias="from")
    event: str = Field(min_length=1)
    to: str = Field(min_length=1)
    guard: str = ""
    actions: list[str] = Field(default_factory=list[str])


class Statechart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    states: list[StateDef] = Field(min_length=1)
    transitions: list[Transition] = Field(default_factory=list[Transition])


class QCD(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quality: QCDLevel = "medium"
    cost: QCDLevel = "medium"
    delivery: QCDDelivery = "normal"
    rationale: str = ""


class Feedback(BaseModel):
    """One trigger->response pair (Nielsen-measurable feedback)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    trigger: str = Field(min_length=1)  # statechart event or stage touchpoint
    surface: str = Field(min_length=1)
    modality: FeedbackModality
    latency_ms: int = Field(default=100, ge=0)
    progress_indicator: bool = False
    description: str = ""


class ExperienceLoop(BaseModel):
    """A closed action->reward loop (game-design lens)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    steps: list[str] = Field(min_length=1)
    reward: str = ""
    cadence: LoopCadence = "session"


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = ""
    surfaces: list[Surface] = Field(default_factory=list[Surface])


class ImportRef(BaseModel):
    """Provenance for a sibling-agent artifact copied into the workspace."""

    model_config = ConfigDict(extra="forbid")

    system: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(min_length=1)
    extracted: list[str] = Field(default_factory=list[str])


class UXContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = SCHEMA_VERSION
    system: Literal["ux-creator"] = SYSTEM
    product: Product
    core_experience: str = Field(min_length=1)
    implementation_spec: list[str] = Field(default_factory=list[str])
    qcd: QCD = Field(default_factory=QCD)
    personas: list[Persona] = Field(default_factory=list[Persona])
    jobs: list[Job] = Field(default_factory=list[Job])
    journeys: list[Journey] = Field(default_factory=list[Journey])
    service_blueprint: ServiceBlueprint | None = None
    statecharts: list[Statechart] = Field(default_factory=list[Statechart])
    feedback: list[Feedback] = Field(default_factory=list[Feedback])
    loops: list[ExperienceLoop] = Field(default_factory=list[ExperienceLoop])
    imports: list[ImportRef] = Field(default_factory=list[ImportRef])

    @model_validator(mode="after")
    def _stage_jobs_known(self) -> UXContract:
        job_ids = {j.id for j in self.jobs}
        unknown = sorted(
            {job for journey in self.journeys for stage in journey.stages for job in stage.jobs}
            - job_ids
        )
        if unknown:
            raise ValueError(f"stage jobs reference unknown job ids: {unknown}")
        return self

    @model_validator(mode="after")
    def _unique_ids(self) -> UXContract:
        for label, items in (
            ("persona", self.personas),
            ("job", self.jobs),
            ("journey", self.journeys),
            ("statechart", self.statecharts),
            ("surface", self.product.surfaces),
            ("feedback", self.feedback),
            ("loop", self.loops),
        ):
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                dupes = sorted(i for i in ids if ids.count(i) > 1)
                raise ValueError(f"duplicate {label} ids: {dupes}")
        return self

    def surface_ids(self) -> set[str]:
        return {s.id for s in self.product.surfaces}


def load_contract(path: Path | str) -> UXContract:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return UXContract.model_validate(data)


def contract_sha256(contract: UXContract) -> str:
    payload = contract.model_dump_json(exclude={"imports"}).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"
