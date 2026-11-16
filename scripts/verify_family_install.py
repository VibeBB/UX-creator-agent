"""Install a SHA-pinned VibeBB family into a new isolated SDK store.

This checks plugin assets and declared cooperation interfaces, not execution,
image readiness, model perception, or product acceptance. Run in a fresh process
with the repository's sdk-check dependency group.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ux_creator.sisters import SISTERS


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Release(StrictModel):
    plugin: str
    repository: str
    source_commit: str = Field(pattern=r"^[a-f0-9]{40}$")
    release: str = Field(pattern=r"^v[0-9]+\.[0-9]+\.[0-9]+$")
    release_url: str
    published_at: str
    repo_path: str

    @model_validator(mode="after")
    def owned_plugin(self) -> Self:
        if self.plugin != "ux" and self.plugin not in SISTERS:
            raise ValueError("unknown VibeBB plugin")
        repo = "UX-creator-agent" if self.plugin == "ux" else SISTERS[self.plugin].repo
        if self.repository != f"VibeBB/{repo}" or self.repo_path != f"plugins/{self.plugin}":
            raise ValueError("source must name the registered VibeBB repository and plugin path")
        if self.release_url != f"https://github.com/{self.repository}/releases/tag/{self.release}":
            raise ValueError("release URL does not match the frozen release")
        return self


class ReleaseLock(StrictModel):
    schema_version: Literal[1]
    scope: Literal["release-pinned-plugin-installation"]
    plugins: list[Release]

    @model_validator(mode="after")
    def complete_family(self) -> Self:
        names = [entry.plugin for entry in self.plugins]
        if len(names) != 11 or set(names) != {"ux", *SISTERS}:
            raise ValueError("lock must contain each of the eleven family plugins exactly once")
        return self


class Inventory(StrictModel):
    plugin: str
    source_commit: str
    release: str
    status: Literal["installed", "error"]
    resolved_commit: str | None = None
    manifest_version: str | None = None
    tree_sha256: str | None = None
    agents: list[str] = Field(default_factory=list[str])
    commands: list[str] = Field(default_factory=list[str])
    mcp_servers: list[str] = Field(default_factory=list[str])
    gaps: list[str] = Field(default_factory=list[str])


class InstallReport(StrictModel):
    scope: Literal["plugin-assets-and-declared-interfaces"] = (
        "plugin-assets-and-declared-interfaces"
    )
    lock_sha256: str
    acceptance: Literal["unknown"] = "unknown"
    tool_readiness: Literal["unknown"] = "unknown"
    workflow_completion: Literal["unknown"] = "unknown"
    plugins: list[Inventory]


def tree_sha256(root: Path) -> str:
    """Hash file paths and bytes; reject links instead of following external files."""
    if root.is_symlink():
        raise ValueError("symlink as asset tree root")
    if not root.is_dir():
        raise ValueError("asset tree unavailable")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink in installed assets: {path.relative_to(root)}")
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def interface_gaps(name: str, agents: list[str], servers: list[str]) -> list[str]:
    expected_agent = "ux-liaison" if name == "ux" else SISTERS[name].liaison_agent
    gaps: list[str] = []
    if name not in servers:
        gaps.append(f"missing declared MCP server: {name}")
    if expected_agent not in agents:
        gaps.append(f"missing native liaison agent: {expected_agent}")
    return gaps


def verify_tag_output(entry: Release, output: str) -> None:
    refs = dict(line.split()[::-1] for line in output.splitlines() if line.strip())
    tag = f"refs/tags/{entry.release}"
    if refs.get(f"{tag}^{{}}", refs.get(tag)) != entry.source_commit:
        raise ValueError("published release tag does not resolve to the pinned source commit")


def install_one(entry: Release, store: Path) -> Inventory:
    # Import after OH_PERSISTENCE_DIR is set: SDK cache constants freeze on import.
    from openhands.sdk.extensions.fetch import (  # pyright: ignore[reportMissingImports]
        fetch_with_resolution,
    )
    from openhands.sdk.plugin import Plugin  # pyright: ignore[reportMissingImports]
    from openhands.sdk.plugin.installed import (  # pyright: ignore[reportMissingImports]
        install_plugin,
    )

    try:
        tag = f"refs/tags/{entry.release}"
        remote = subprocess.run(
            ["git", "ls-remote", f"https://github.com/{entry.repository}.git", tag, f"{tag}^{{}}"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        verify_tag_output(entry, remote.stdout)
        # SDK installation dereferences links. Inspect the fetched source before
        # copying, so an external target cannot become an apparently ordinary asset.
        fetched, resolved = fetch_with_resolution(
            source=f"https://github.com/{entry.repository}.git",
            cache_dir=store.parent / "sdk-state/cache/extensions",
            ref=entry.source_commit,
            repo_path=entry.repo_path,
        )
        if resolved != entry.source_commit:
            raise ValueError("SDK fetched a different source commit")
        if fetched.parent.is_symlink():
            raise ValueError("symlink in source plugin path")
        source_sha256 = tree_sha256(fetched)
        info = install_plugin(
            f"https://github.com/{entry.repository}.git",
            ref=entry.source_commit,
            repo_path=entry.repo_path,
            installed_dir=store,
        )
        if info.resolved_ref != entry.source_commit:
            raise ValueError("SDK resolved a different source commit")
        installed_sha256 = tree_sha256(info.install_path)
        if installed_sha256 != source_sha256:
            raise ValueError("installed assets differ from the checked source tree")
        plugin = Plugin.load(info.install_path)
        if plugin.name != entry.plugin:
            raise ValueError("installed manifest has a different plugin name")
        agents = sorted(agent.name for agent in plugin.agents)
        servers = sorted(plugin.mcp_config)
        return Inventory(
            plugin=entry.plugin,
            source_commit=entry.source_commit,
            release=entry.release,
            status="installed",
            resolved_commit=info.resolved_ref,
            manifest_version=plugin.version,
            tree_sha256=installed_sha256,
            agents=agents,
            commands=sorted(command.name for command in plugin.commands),
            mcp_servers=servers,
            gaps=interface_gaps(entry.plugin, agents, servers),
        )
    except Exception as error:
        return Inventory(
            plugin=entry.plugin,
            source_commit=entry.source_commit,
            release=entry.release,
            status="error",
            gaps=[f"{type(error).__name__}: {error}"],
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new evidence directory")
    args = parser.parse_args()
    lock_path: Path = args.lock
    destination: Path = args.out.resolve()
    lock_bytes = lock_path.read_bytes()
    lock = ReleaseLock.model_validate_json(lock_bytes)
    if "openhands.sdk" in sys.modules:
        raise RuntimeError("run this verifier in a fresh process to isolate SDK persistence")
    destination.mkdir(parents=True, exist_ok=False)
    os.environ["OH_PERSISTENCE_DIR"] = str(destination / "sdk-state")
    os.environ["OPENHANDS_SUPPRESS_BANNER"] = "1"
    (destination / "lock.json").write_bytes(lock_bytes)
    results: list[Inventory] = []
    for entry in lock.plugins:
        item = install_one(entry, destination / "installed")
        results.append(item)
        report = InstallReport(lock_sha256=hashlib.sha256(lock_bytes).hexdigest(), plugins=results)
        (destination / "report.json").write_text(
            report.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        print(item.model_dump_json(), flush=True)
    return int(any(item.status != "installed" or item.gaps for item in results))


if __name__ == "__main__":
    raise SystemExit(main())
