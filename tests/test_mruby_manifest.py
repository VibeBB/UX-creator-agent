"""mruby/c manifest: detection, generation, and the check gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ux_creator.cli import main
from ux_creator.mruby_manifest import (
    MrubyRequires,
    build_manifest,
    detect_requires,
    list_ruby_sources,
    manifest_problems,
    render_manifest,
)


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    ux = tmp_path / "ux"
    ux.mkdir()
    (ux / "app.rb").write_text(
        "def loop\n  led(1) if button?\n  sleep_ms(10)\nend\n", encoding="utf-8"
    )
    return tmp_path


class TestDetect:
    def test_plain_source(self) -> None:
        req = detect_requires("def x\n  1 + 2\nend\n")
        assert req.float == 0 and not req.math and not req.utf8

    def test_string_and_tick(self, project: Path) -> None:
        req = detect_requires((project / "ux/app.rb").read_text())
        assert req.tick  # sleep_ms
        assert not req.utf8

    def test_float_and_math(self) -> None:
        req = detect_requires("x = 3.5\ny = Math.sqrt(x)\n")
        assert req.float == 1 and req.math

    def test_string_usage(self) -> None:
        assert detect_requires('name = "a".upcase\n').string
        assert detect_requires('"value: #{x}"\n').string

    def test_utf8(self) -> None:
        assert detect_requires('msg = "こんにちは"\n').utf8


class TestBuild:
    def test_manifest_shape(self, project: Path) -> None:
        sources = list_ruby_sources(project / "ux")
        manifest = build_manifest("kettle", sources, project)
        assert manifest.artifact_kind == "mruby_manifest"
        assert manifest.files[0].file == "ux/app.rb"
        assert len(manifest.files[0].sha256) == 64
        assert manifest.requires.tick

    def test_dsl_files_excluded(self, project: Path) -> None:
        (project / "ux" / "design.ux.rb").write_text("UX.design {}\n", encoding="utf-8")
        sources = list_ruby_sources(project / "ux")
        assert [p.name for p in sources] == ["app.rb"]

    def test_requires_override(self, project: Path) -> None:
        manifest = build_manifest(
            "k", list_ruby_sources(project / "ux"), project, MrubyRequires(float=2)
        )
        assert manifest.requires.float == 2

    def test_render_is_deterministic(self, project: Path) -> None:
        manifest = build_manifest("k", list_ruby_sources(project / "ux"), project)
        assert render_manifest(manifest) == render_manifest(manifest)


class TestCheckGate:
    def _write_manifest(self, project: Path) -> Path:
        out = project / "ux" / "kettle.mruby-manifest.json"
        manifest = build_manifest("kettle", list_ruby_sources(project / "ux"), project)
        out.write_text(render_manifest(manifest), encoding="utf-8")
        return out

    def test_fresh_manifest_passes(self, project: Path) -> None:
        assert manifest_problems(self._write_manifest(project), project) == []

    def test_stale_source_fails(self, project: Path) -> None:
        out = self._write_manifest(project)
        (project / "ux/app.rb").write_text("# changed\n", encoding="utf-8")
        assert any("stale" in p for p in manifest_problems(out, project))

    def test_unlisted_source_fails(self, project: Path) -> None:
        out = self._write_manifest(project)
        (project / "ux/extra.rb").write_text("x = 1\n", encoding="utf-8")
        assert any("not listed" in p for p in manifest_problems(out, project))

    def test_missing_source_fails(self, project: Path) -> None:
        out = self._write_manifest(project)
        (project / "ux/app.rb").unlink()
        assert any("missing" in p for p in manifest_problems(out, project))

    def test_under_declared_requires_fails(self, project: Path) -> None:
        out = self._write_manifest(project)
        doc = json.loads(out.read_text())
        doc["requires"]["tick"] = False
        out.write_text(json.dumps(doc), encoding="utf-8")
        assert any("tick" in p for p in manifest_problems(out, project))

    def test_unreadable_manifest_fails(self, project: Path) -> None:
        out = project / "ux/k.mruby-manifest.json"
        out.write_text("{not json", encoding="utf-8")
        assert any("unreadable" in p for p in manifest_problems(out, project))


class TestCli:
    def test_generate_then_check(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert (
            main(
                [
                    "mruby-manifest",
                    "--dir",
                    str(project / "ux"),
                    "--product",
                    "kettle",
                    "--root",
                    str(project),
                ]
            )
            == 0
        )
        out = json.loads(capsys.readouterr().out)
        assert out["verdict"] == "pass" and out["files"] == 1
        assert (
            main(
                [
                    "mruby-manifest",
                    "--dir",
                    str(project / "ux"),
                    "--product",
                    "kettle",
                    "--root",
                    str(project),
                    "--check",
                ]
            )
            == 0
        )

    def test_check_missing_manifest(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert (
            main(
                [
                    "mruby-manifest",
                    "--dir",
                    str(project / "ux"),
                    "--product",
                    "kettle",
                    "--root",
                    str(project),
                    "--check",
                ]
            )
            == 1
        )
        assert "missing" in json.loads(capsys.readouterr().out)["problems"][0]

    def test_empty_dir_fails(self, tmp_path: Path) -> None:
        (tmp_path / "ux").mkdir()
        assert (
            main(
                ["mruby-manifest", "--dir", str(tmp_path / "ux"), "--product", "k"]
            )
            == 1
        )

    def test_not_a_dir_fails(self, tmp_path: Path) -> None:
        assert main(["mruby-manifest", "--dir", str(tmp_path / "no"), "--product", "k"]) == 1
