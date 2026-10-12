"""Device API specs (``*.mruby-api.json``) authored by UX.

The UX agent designs the *Ruby-ness* of device-specific mruby/c classes
and methods: naming, keyword-vs-positional shape, enums, docs and access
levels. The spec is the JSON contract handed to firmware-agent, which
pins it by sha256 (``mrubyc.device_api``) and generates the C bindings;
simulation/dashboard generate stubs from the same document.

The schema mirrors ``firmware.mruby_api`` field-for-field — the JSON is
the contract, never shared code. On top of structural validity this
module adds the UX-side checks: Ruby idiom lint (``rubyness_problems``),
manifest class collision, and ``*.rb`` usage coverage so a spec method a
UX source calls actually exists.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

ARTIFACT_KIND = "mruby_api"
SCHEMA_VERSION = 1
SPEC_SUFFIX = ".mruby-api.json"

PARAM_TYPES = ("int", "float", "bool", "symbol", "string", "array<int>")
RETURN_TYPES = (*PARAM_TYPES, "nil", "array<float>")
RESERVED_ARG_NAMES = {"rest", "blk"}

_CLASS_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_CONST_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_METHOD_RE = re.compile(r"^[a-z_][a-z0-9_]*[?!]?$")
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_CLASS_DECL_RE = re.compile(r"^\s*class\s+([A-Z][A-Za-z0-9]*)", re.MULTILINE)
_API_CALL_RE = re.compile(r"\b([A-Z][A-Za-z0-9]*)\.(\w+[?!]?)")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApiSymbol(_Strict):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    const: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")


class ApiParam(_Strict):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    type: str = Field(pattern=r"^(int|float|bool|symbol|string|array<int>)$")
    required: bool = True
    default: int | float | bool | str | None = None
    enum: list[str] = Field(default_factory=list[str])
    max_len: int = Field(default=0, ge=0, le=65535)
    c_type: str = Field(
        default="",
        pattern=r"^(|mrbc_int_t|mrbc_float_t|int32_t|int|const char \*)$",
    )


class ApiReturn(_Strict):
    type: str = Field(pattern=r"^(nil|int|float|bool|symbol|string|array<int>|array<float>)$")
    cap: int = Field(default=0, ge=0, le=65535)


class ApiMethod(_Strict):
    name: str = Field(pattern=r"^[a-z_][a-z0-9_]*[?!]?$")
    doc: str = ""
    params: list[ApiParam] = Field(default_factory=list[ApiParam])
    kwargs: list[ApiParam] = Field(default_factory=list[ApiParam])
    rest_kwargs: bool = False
    block: str = Field(default="none", pattern=r"^(none|required|optional)$")
    returns: ApiReturn = Field(default_factory=lambda: ApiReturn(type="nil"))
    access: str = Field(default="any", pattern=r"^(any|system_task|expert)$")
    arg_errors: str = Field(default="raise", pattern=r"^(raise|silent)$")
    handler: str = Field(pattern=r"^[a-z_][a-z0-9_]*$")


class ApiInstance(_Strict):
    data_size: int = Field(ge=4, le=4096)
    constructor: str = Field(pattern=r"^[a-z_][a-z0-9_]*$")
    destructor: str = Field(default="", pattern=r"^$|^[a-z_][a-z0-9_]*$")


class ApiConst(_Strict):
    name: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    value: int | float | bool | str


class ApiClass(_Strict):
    name: str = Field(pattern=r"^[A-Z][A-Za-z0-9]*$")
    kind: str = Field(default="class", pattern=r"^(class|module)$")
    outer: str = ""
    super: str = ""
    doc: str = ""
    constants: list[ApiConst] = Field(default_factory=list[ApiConst])
    methods: list[ApiMethod] = Field(default_factory=list[ApiMethod])
    init: str = Field(default="", pattern=r"^$|^[a-z_][a-z0-9_]*$")
    instance: ApiInstance | None = None


class ApiSystemTask(_Strict):
    vm_id: int = Field(ge=1, le=255)


class MrubyApiSpec(_Strict):
    """The ``*.mruby-api.json`` document firmware pins and generates from."""

    schema_version: int = 1
    artifact_kind: str = ARTIFACT_KIND
    product: str = Field(min_length=1)
    symbols: list[ApiSymbol] = Field(default_factory=list[ApiSymbol])
    classes: list[ApiClass] = Field(min_length=1)
    system_task: ApiSystemTask | None = None
    expert_define: str = Field(default="", pattern=r"^$|^[A-Z_][A-Z0-9_]*$")

    @model_validator(mode="after")
    def _cross_validate(self) -> MrubyApiSpec:
        names = [c.name for c in self.classes]
        if len(set(names)) != len(names):
            raise ValueError("class names must be unique")
        symbol_names = {s.name for s in self.symbols}
        symbol_consts = [s.const for s in self.symbols]
        if len(set(symbol_consts)) != len(symbol_consts):
            raise ValueError("symbol consts must be unique")
        class_names = set(names)
        for cls in self.classes:
            if cls.outer and cls.outer not in class_names:
                raise ValueError(f"{cls.name}.outer {cls.outer} not a declared class")
            if cls.super and cls.super not in class_names:
                raise ValueError(f"{cls.name}.super {cls.super} not a declared class")
            if cls.kind == "module" and cls.instance is not None:
                raise ValueError(f"{cls.name}: modules cannot carry instance data")
            if cls.instance is None and any(m.name == "new" for m in cls.methods):
                raise ValueError(f"{cls.name}: 'new' is reserved for instance classes")
            meth_names = [m.name for m in cls.methods]
            if len(set(meth_names)) != len(meth_names):
                raise ValueError(f"{cls.name}: method names must be unique")
            for method in cls.methods:
                for param in [*method.params, *method.kwargs]:
                    if param.name in RESERVED_ARG_NAMES:
                        raise ValueError(f"{cls.name}.{method.name}: {param.name} is reserved")
                    if param.type == "symbol" and param.enum:
                        unknown = set(param.enum) - symbol_names
                        if unknown:
                            raise ValueError(
                                f"{cls.name}.{method.name}.{param.name}: enum "
                                f"{sorted(unknown)} not in declared symbols"
                            )
                    if param.type == "array<int>" and param.max_len == 0:
                        raise ValueError(
                            f"{cls.name}.{method.name}.{param.name}: array<int> needs max_len"
                        )
                    if param.type == "string" and param.max_len == 0:
                        raise ValueError(
                            f"{cls.name}.{method.name}.{param.name}: string needs max_len"
                        )
                if method.returns.type in {"string", "array<int>", "array<float>"} and (
                    method.returns.cap == 0
                ):
                    raise ValueError(
                        f"{cls.name}.{method.name}: {method.returns.type} return needs cap"
                    )
                if method.access == "system_task" and self.system_task is None:
                    raise ValueError(
                        f"{cls.name}.{method.name}: system_task access needs a system_task block"
                    )
                if method.access == "expert" and not self.expert_define:
                    raise ValueError(f"{cls.name}.{method.name}: expert access needs expert_define")
        return self


def detect_classes(source: str) -> list[str]:
    """Class names the ``.rb`` source itself defines."""
    return _CLASS_DECL_RE.findall(source)


def detect_api_uses(source: str, spec: MrubyApiSpec) -> dict[str, set[str]]:
    """``Class.method`` call sites whose class is declared by the spec."""
    class_names = {c.name for c in spec.classes}
    uses: dict[str, set[str]] = {}
    for cls_name, method in _API_CALL_RE.findall(source):
        if cls_name in class_names:
            uses.setdefault(cls_name, set()).add(method)
    return uses


def usage_problems(source: str, spec: MrubyApiSpec, source_name: str) -> list[str]:
    """Spec-method calls in ``.rb`` code that the spec does not declare."""
    problems: list[str] = []
    methods = {c.name: {m.name for m in c.methods} for c in spec.classes}
    instance_classes = {c.name for c in spec.classes if c.instance is not None}
    for cls_name, called in sorted(detect_api_uses(source, spec).items()):
        allowed = set(methods[cls_name])
        if cls_name in instance_classes:
            allowed.add("new")
        missing = called - allowed
        for name in sorted(missing):
            problems.append(f"{source_name}: {cls_name}.{name} not declared in the api spec")
    return problems


def rubyness_problems(spec: MrubyApiSpec) -> list[str]:
    """Ruby-idiom lint over an already-valid spec.

    The API surface is user experience: Ruby callers expect verb-first
    snake_case methods, `?` predicates, `!` for danger, keyword args for
    options, symbols for finite choices, blocks for callbacks and
    UP_CASE constants. Each violation is a problem, not a warning — the
    gate is the design review.
    """
    problems: list[str] = []
    for cls in spec.classes:
        if not _CLASS_RE.match(cls.name):
            problems.append(f"{cls.name}: class names are CamelCase")
        if not cls.doc.strip():
            problems.append(f"{cls.name}: class needs a doc line for the API reference")
        if cls.instance is not None and not cls.instance.constructor:
            problems.append(f"{cls.name}: instance classes need a constructor handler")
        const_names = [c.name for c in cls.constants]
        if len(set(const_names)) != len(const_names):
            problems.append(f"{cls.name}: constant names must be unique")
        for const in cls.constants:
            if not _CONST_RE.match(const.name):
                problems.append(f"{cls.name}.{const.name}: constants are UPPER_SNAKE")
        for method in cls.methods:
            label = f"{cls.name}.{method.name}"
            if not _METHOD_RE.match(method.name):
                problems.append(f"{label}: method names are snake_case, ? or !")
            if not method.doc.strip():
                problems.append(f"{label}: method needs a doc line for the API reference")
            if method.name.endswith("?") and method.returns.type != "bool":
                problems.append(f"{label}: ? methods return bool")
            if method.name.endswith("!") and not method.doc.strip():
                problems.append(f"{label}: ! methods must document what they mutate")
            if method.name.startswith(("get_", "set_")):
                problems.append(
                    f"{label}: get_/set_ prefixes are un-Ruby; use an attribute name or a verb"
                )
            if len(method.params) > 3:
                problems.append(
                    f"{label}: {len(method.params)} positional args; move options to keyword args"
                )
            if method.name.startswith("on_") and method.block == "none":
                problems.append(f"{label}: on_* callbacks should take a block")
            for param in method.params:
                if not _NAME_RE.match(param.name):
                    problems.append(f"{label}: param {param.name} is not snake_case")
                if param.type == "symbol" and not param.enum:
                    problems.append(
                        f"{label}.{param.name}: symbol params declare their enum "
                        "so callers see the allowed parts"
                    )
                if param.type == "bool" and param.name.startswith("is_"):
                    problems.append(
                        f"{label}.{param.name}: is_ prefix on an argument is "
                        "un-Ruby; name the state"
                    )
            for param in method.kwargs:
                if not _NAME_RE.match(param.name):
                    problems.append(f"{label}: kwarg {param.name} is not snake_case")
                if param.type == "symbol" and not param.enum:
                    problems.append(f"{label}.{param.name}: symbol kwargs declare their enum")
    return problems


def render_api_doc(spec: MrubyApiSpec) -> str:
    """Markdown API reference generated from the spec (the user-facing doc)."""
    lines = [
        f"# {spec.product} device API",
        "",
        f"Generated from `{spec.product}.mruby-api.json` — the UX-authored contract.",
        "",
    ]
    for cls in spec.classes:
        head = cls.name if not cls.outer else f"{cls.outer}::{cls.name}"
        lines += [f"## `{head}` ({cls.kind})", ""]
        if cls.doc:
            lines += [cls.doc, ""]
        if cls.instance is not None:
            lines += [
                f"Instance class: `{cls.instance.data_size}` bytes of driver state per object.",
                "",
            ]
        if cls.constants:
            lines.append("### Constants")
            lines.append("")
            for const in cls.constants:
                lines.append(f"- `{cls.name}::{const.name}` = `{const.value}`")
            lines.append("")
        if cls.methods:
            lines.append("### Methods")
            lines.append("")
            for method in cls.methods:
                sig = _signature(method)
                lines.append(f"- `{head}.{method.name}{sig}` → `{method.returns.type}`")
                if method.doc:
                    lines.append(f"  - {method.doc}")
                if method.access != "any":
                    lines.append(f"  - Access: `{method.access}`")
            lines.append("")
    if spec.symbols:
        lines += ["## Symbols", ""]
        for sym in spec.symbols:
            lines.append(f"- `:{sym.name}` → handler constant `{sym.const}`")
        lines.append("")
    return "\n".join(lines)


def _signature(method: ApiMethod) -> str:
    parts = [p.name for p in method.params]
    parts += [f"{k.name}:" for k in method.kwargs]
    if method.rest_kwargs:
        parts.append("**rest")
    if method.block != "none":
        parts.append("{ ... }" if method.block == "optional" else "{ |..| }")
    return f"({', '.join(parts)})" if parts else ""


def spec_problems(path: Path) -> tuple[list[str], MrubyApiSpec | None]:
    """Parse + validate the spec file; returns problems and the spec."""
    try:
        spec = MrubyApiSpec.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{path.name} invalid: {exc}"], None
    if spec.artifact_kind != ARTIFACT_KIND:
        return [f"{path.name}: artifact_kind must be {ARTIFACT_KIND}"], None
    if spec.schema_version != SCHEMA_VERSION:
        return [f"{path.name}: schema_version must be {SCHEMA_VERSION}"], None
    return [], spec


def api_problems(
    spec: MrubyApiSpec,
    spec_path: Path,
    ruby_sources: list[Path],
    manifest_classes: list[str],
) -> list[str]:
    """Full UX-side gate: rubyness + collisions + usage coverage."""
    problems = rubyness_problems(spec)
    spec_classes = {c.name for c in spec.classes}
    clash = spec_classes & set(manifest_classes)
    if clash:
        problems.append(
            "api classes collide with classes defined in ux .rb sources: "
            + ", ".join(sorted(clash))
        )
    for source in ruby_sources:
        text = source.read_text(encoding="utf-8", errors="replace")
        if clash & set(detect_classes(text)):
            problems.append(
                f"{source.name}: defines a class the api spec declares; pick another name"
            )
        problems += usage_problems(text, spec, source.name)
        unknown_symbols = _symbol_uses(text, spec)
        for sym in sorted(unknown_symbols):
            problems.append(f"{source.name}: :{sym} not declared in the api spec symbols")
    if spec_path.name.startswith(spec.product):
        pass  # naming is conventional, not enforced
    return problems


def _symbol_uses(source: str, spec: MrubyApiSpec) -> set[str]:
    """`:name` literals that match a spec symbol enum context."""
    declared = {s.name for s in spec.symbols}
    if not declared:
        return set()
    used = set(re.findall(r":([a-z][a-z0-9_]*)", source))
    # Only flag symbols passed to api classes — a plain `:foo` elsewhere
    # is UX-local. Approximation: flag used-but-undeclared only when the
    # source also calls a spec class with a symbol param.
    class_names = "|".join(re.escape(c.name) for c in spec.classes)
    calls_spec = re.search(rf"\b({class_names})\.", source)
    if not calls_spec:
        return set()
    return used - declared - _non_api_symbols(source, spec)


def _non_api_symbols(source: str, spec: MrubyApiSpec) -> set[str]:
    """Symbols appearing outside `Class.method` call argument lists.

    Conservative: any symbol on a line that does not mention a spec
    class is UX-local and exempt.
    """
    class_names = "|".join(re.escape(c.name) for c in spec.classes)
    local: set[str] = set()
    for line in source.splitlines():
        if not re.search(rf"\b({class_names})\.", line):
            local.update(re.findall(r":([a-z][a-z0-9_]*)", line))
    return local
