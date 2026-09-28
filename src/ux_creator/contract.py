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
import re
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


ControlKind = Literal["button", "touch", "dial", "switch", "link", "gesture"]


class Control(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    surface: str = Field(min_length=1)
    kind: ControlKind = "touch"
    touchpoint: str = ""
    width_mm: float | None = Field(default=None, gt=0)
    height_mm: float | None = Field(default=None, gt=0)
    fg: str = ""
    bg: str = ""
    large_text: bool = False


_HEX6 = re.compile(r"^#[0-9A-Fa-f]{6}$")

ColorRole = Literal["primary", "secondary", "accent", "signal", "neutral"]
Gloss = Literal["matte", "satin", "gloss"]
MarkingKind = Literal["logo", "wordmark", "label", "icon", "regulatory", "instruction"]
MarkingMethod = Literal[
    "print", "pad_print", "screen_print", "laser", "emboss", "deboss", "mold_in", "sticker"
]


class CMFColor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = ""
    hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    role: ColorRole = "primary"


class CMFMaterial(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    process: str = ""
    notes: str = ""


class CMFFinish(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    gloss: Gloss = "matte"
    texture: str = ""


class CMFPart(BaseModel):
    """One surface's color, material, and finish."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    surface: str = Field(min_length=1)
    color: str = Field(min_length=1)
    material: str = Field(min_length=1)
    finish: str = ""
    notes: str = ""


class CMFMarking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    surface: str = Field(min_length=1)
    kind: MarkingKind
    content: str = Field(min_length=1)
    method: MarkingMethod = "print"
    color: str = ""


class CMF(BaseModel):
    """Industrial design / CMF: form language plus color, material, finish, marking."""

    model_config = ConfigDict(extra="forbid")

    form_language: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list[str], max_length=5)
    references: list[str] = Field(default_factory=list[str])
    palette: list[CMFColor] = Field(min_length=1)
    materials: list[CMFMaterial] = Field(min_length=1)
    finishes: list[CMFFinish] = Field(default_factory=list[CMFFinish])
    parts: list[CMFPart] = Field(min_length=1)
    markings: list[CMFMarking] = Field(default_factory=list[CMFMarking])


ContentSourceKind = Literal["bard_cue", "file", "inline"]


class ContentSource(BaseModel):
    """Where a content asset comes from: a bard cue, a workspace file, or an inline spec."""

    model_config = ConfigDict(extra="forbid")

    kind: ContentSourceKind
    ref: str = ""  # workspace path (bard cues.json or asset file)
    cue: str = ""  # bard cue id when kind == "bard_cue"
    spec: str = ""  # inline pattern (LED, haptic, motion) when kind == "inline"


class ContentAsset(BaseModel):
    """Interaction content that realizes one feedback record."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    feedback: str = Field(min_length=1)
    modality: FeedbackModality
    source: ContentSource
    duration_ms: int | None = Field(default=None, ge=1, le=60000)
    loop: bool = False
    notes: str = ""


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
    controls: list[Control] = Field(default_factory=list[Control])
    loops: list[ExperienceLoop] = Field(default_factory=list[ExperienceLoop])
    imports: list[ImportRef] = Field(default_factory=list[ImportRef])
    cmf: CMF | None = None
    content: list[ContentAsset] = Field(default_factory=list[ContentAsset])

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
    def _controls_known(self) -> UXContract:
        surface_ids = {s.id for s in self.product.surfaces}
        touchpoints = {
            tp for journey in self.journeys for stage in journey.stages for tp in stage.touchpoints
        }
        for control in self.controls:
            if control.surface not in surface_ids:
                raise ValueError(f"control {control.id}: unknown surface {control.surface!r}")
            if control.touchpoint and control.touchpoint not in touchpoints:
                raise ValueError(f"control {control.id}: unknown touchpoint {control.touchpoint!r}")
            if bool(control.fg) != bool(control.bg):
                raise ValueError(f"control {control.id}: fg and bg must both be set or both empty")
            for name, color in (("fg", control.fg), ("bg", control.bg)):
                if color and not _HEX6.match(color):
                    raise ValueError(f"control {control.id}: {name} {color!r} is not #RRGGBB")
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
            ("control", self.controls),
            ("content", self.content),
            ("cmf color", self.cmf.palette if self.cmf else []),
            ("cmf material", self.cmf.materials if self.cmf else []),
            ("cmf finish", self.cmf.finishes if self.cmf else []),
            ("cmf part", self.cmf.parts if self.cmf else []),
            ("cmf marking", self.cmf.markings if self.cmf else []),
        ):
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                dupes = sorted(i for i in ids if ids.count(i) > 1)
                raise ValueError(f"duplicate {label} ids: {dupes}")
        return self

    @model_validator(mode="after")
    def _cmf_refs_known(self) -> UXContract:
        if self.cmf is None:
            return self
        surface_ids = {s.id for s in self.product.surfaces}
        colors = {c.id for c in self.cmf.palette}
        materials = {m.id for m in self.cmf.materials}
        finishes = {f.id for f in self.cmf.finishes}
        for part in self.cmf.parts:
            if part.surface not in surface_ids:
                raise ValueError(f"cmf part {part.id}: unknown surface {part.surface!r}")
            if part.color not in colors:
                raise ValueError(f"cmf part {part.id}: unknown color {part.color!r}")
            if part.material not in materials:
                raise ValueError(f"cmf part {part.id}: unknown material {part.material!r}")
            if part.finish and part.finish not in finishes:
                raise ValueError(f"cmf part {part.id}: unknown finish {part.finish!r}")
        for marking in self.cmf.markings:
            if marking.surface not in surface_ids:
                raise ValueError(f"cmf marking {marking.id}: unknown surface {marking.surface!r}")
            if marking.color and marking.color not in colors:
                raise ValueError(f"cmf marking {marking.id}: unknown color {marking.color!r}")
        return self

    @model_validator(mode="after")
    def _content_refs_known(self) -> UXContract:
        feedback_ids = {f.id for f in self.feedback}
        for asset in self.content:
            if asset.feedback not in feedback_ids:
                raise ValueError(f"content {asset.id}: unknown feedback {asset.feedback!r}")
            src = asset.source
            if src.kind == "bard_cue":
                if asset.modality != "audio":
                    raise ValueError(f"content {asset.id}: bard_cue sources are audio only")
                if not src.ref or not src.cue:
                    raise ValueError(f"content {asset.id}: bard_cue needs ref and cue")
                if src.spec:
                    raise ValueError(f"content {asset.id}: spec is only for inline sources")
            elif src.kind == "file":
                if not src.ref or src.cue or src.spec:
                    raise ValueError(f"content {asset.id}: file sources need ref only")
            elif not src.spec or src.ref or src.cue:
                raise ValueError(f"content {asset.id}: inline sources need spec only")
        return self

    def surface_ids(self) -> set[str]:
        return {s.id for s in self.product.surfaces}


def load_contract(path: Path | str) -> UXContract:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return UXContract.model_validate(data)


def contract_sha256(contract: UXContract) -> str:
    payload = contract.model_dump_json(exclude={"imports"}).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"
