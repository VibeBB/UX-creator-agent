"""``*.mruby-api.json`` spec validation, rubyness lint and usage gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ux_creator.mruby_api import (
    MrubyApiSpec,
    api_problems,
    detect_api_uses,
    detect_classes,
    render_api_doc,
    rubyness_problems,
    spec_problems,
    usage_problems,
)

EXAMPLE = Path("examples/mruby-ux")
SPEC_PATH = EXAMPLE / "api/mruby-ux.mruby-api.json"


def _spec_json() -> dict[str, Any]:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _spec() -> MrubyApiSpec:
    return MrubyApiSpec.model_validate(_spec_json())


def _app() -> Path:
    return EXAMPLE / "ux/app.rb"


class TestSchema:
    def test_example_spec_validates(self) -> None:
        spec = _spec()
        assert [c.name for c in spec.classes] == ["LED", "Sample"]
        assert spec.system_task is not None and spec.system_task.vm_id == 1
        assert spec.expert_define == "FW_DEBUG_API"

    def test_symbol_enum_must_exist(self) -> None:
        bad = _spec_json()
        bad["classes"][0]["methods"][1]["params"][0]["enum"] = ["nope"]
        with pytest.raises(ValueError, match="enum"):
            MrubyApiSpec.model_validate(bad)

    def test_system_task_requires_block(self) -> None:
        bad = _spec_json()
        del bad["system_task"]
        with pytest.raises(ValueError, match="system_task"):
            MrubyApiSpec.model_validate(bad)

    def test_module_rejects_instance(self) -> None:
        bad = _spec_json()
        bad["classes"][1]["kind"] = "module"
        with pytest.raises(ValueError, match="module"):
            MrubyApiSpec.model_validate(bad)

    def test_reserved_param_names(self) -> None:
        bad = _spec_json()
        bad["classes"][0]["methods"][0]["kwargs"].append({"name": "blk", "type": "int"})
        with pytest.raises(ValueError, match="reserved"):
            MrubyApiSpec.model_validate(bad)


class TestRubyness:
    def test_example_is_clean(self) -> None:
        assert rubyness_problems(_spec()) == []

    def test_missing_docs(self) -> None:
        bad = _spec_json()
        bad["classes"][0]["doc"] = ""
        probs = rubyness_problems(MrubyApiSpec.model_validate(bad))
        assert any("LED" in p and "doc" in p for p in probs)

    def test_question_mark_needs_bool(self) -> None:
        bad = _spec_json()
        bad["classes"][0]["methods"][2]["name"] = "all?"
        assert any("all?" in p for p in rubyness_problems(MrubyApiSpec.model_validate(bad)))

    def test_get_set_prefix(self) -> None:
        bad = _spec_json()
        bad["classes"][0]["methods"][0]["name"] = "set_state"
        probs = rubyness_problems(MrubyApiSpec.model_validate(bad))
        assert any("set_" in p and "un-Ruby" in p for p in probs)

    def test_on_star_needs_block(self) -> None:
        bad = _spec_json()
        bad["classes"][0]["methods"][5]["block"] = "none"
        probs = rubyness_problems(MrubyApiSpec.model_validate(bad))
        assert any("on_change" in p and "block" in p for p in probs)

    def test_symbol_needs_enum(self) -> None:
        bad = _spec_json()
        del bad["classes"][0]["methods"][1]["params"][0]["enum"]
        probs = rubyness_problems(MrubyApiSpec.model_validate(bad))
        assert any("enum" in p for p in probs)

    def test_too_many_positional(self) -> None:
        bad = _spec_json()
        bad["classes"][0]["methods"][1]["params"] = [
            {"name": f"p{i}", "type": "int"} for i in range(4)
        ]
        probs = rubyness_problems(MrubyApiSpec.model_validate(bad))
        assert any("positional" in p for p in probs)


class TestUsage:
    def test_detect_classes(self) -> None:
        text = _app().read_text(encoding="utf-8")
        assert detect_classes(text) == ["Ux"]

    def test_detect_api_uses(self) -> None:
        text = _app().read_text(encoding="utf-8")
        uses = detect_api_uses(text, _spec())
        assert uses["LED"] == {"set", "toggle", "all", "on_change"}

    def test_undeclared_method_call_fails(self) -> None:
        source = "LED.toggel(:led1)\n"
        probs = usage_problems(source, _spec(), "app.rb")
        assert probs == ["app.rb: LED.toggel not declared in the api spec"]

    def test_instance_new_allowed(self) -> None:
        source = "s = Sample.new\ns.read(0)\n"
        assert usage_problems(source, _spec(), "app.rb") == []

    def test_collision_with_ruby_classes(self) -> None:
        probs = api_problems(_spec(), SPEC_PATH, [_app()], manifest_classes=["Ux", "LED"])
        assert any("collide" in p and "LED" in p for p in probs)

    def test_undeclared_symbol_fails(self) -> None:
        src = _app().read_text(encoding="utf-8").replace(":led1", ":led9")
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            rb = Path(td) / "app.rb"
            rb.write_text(src, encoding="utf-8")
            probs = api_problems(_spec(), SPEC_PATH, [rb], manifest_classes=[])
        assert any(":led9" in p for p in probs)


class TestGate:
    def test_spec_problems_ok(self) -> None:
        problems, spec = spec_problems(SPEC_PATH)
        assert problems == []
        assert spec is not None

    def test_example_clean_end_to_end(self) -> None:
        _problems, spec = spec_problems(SPEC_PATH)
        assert spec is not None
        full = api_problems(spec, SPEC_PATH, [_app()], manifest_classes=["Ux"])
        assert full == []

    def test_render_doc(self) -> None:
        doc = render_api_doc(_spec())
        assert "`LED.set(part:, state:)` → `bool`" in doc
        assert "`LED::OFF` = `0`" in doc
        assert "Access: `system_task`" in doc
        assert "`:led1` → handler constant `kFwHwLed1`" in doc


class TestCli:
    def test_check_pass_and_fail(self, capsys: pytest.CaptureFixture[str]) -> None:
        from ux_creator.cli import main

        rc = main(
            [
                "mruby-api",
                str(SPEC_PATH),
                "--ruby-dir",
                str(EXAMPLE / "ux"),
                "--check",
            ]
        )
        out = json.loads(capsys.readouterr().out)
        assert rc == 0 and out["verdict"] == "pass"
        assert out["classes"] == ["LED", "Sample"]

    def test_doc_render(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from ux_creator.cli import main

        doc = tmp_path / "api.md"
        rc = main(
            [
                "mruby-api",
                str(SPEC_PATH),
                "--ruby-dir",
                str(EXAMPLE / "ux"),
                "--doc-out",
                str(doc),
            ]
        )
        out = json.loads(capsys.readouterr().out)
        assert rc == 0 and out["verdict"] == "pass"
        assert "`LED.set" in doc.read_text(encoding="utf-8")

    def test_invalid_spec_fails(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from ux_creator.cli import main

        bad = tmp_path / "bad.mruby-api.json"
        bad.write_text('{"classes": []}', encoding="utf-8")
        rc = main(["mruby-api", str(bad), "--check"])
        out = json.loads(capsys.readouterr().out)
        assert rc == 1 and out["verdict"] == "fail"
