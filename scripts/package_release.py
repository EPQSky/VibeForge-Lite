#!/usr/bin/env python3
"""Build a deterministic local Marketplace and release archive."""

from __future__ import annotations

import argparse
import gzip
import json
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATHS = (
    ".codex-plugin",
    "skills",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "UPSTREAM.lock",
    "licenses",
)
SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".npmrc",
    ".pypirc",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
ABSOLUTE_HOME_RE = re.compile(
    rb"(?:"
    rb"/(?:home|Users)/[^/\s`]+(?:/|(?=\s|$))"
    rb"|(?i:[A-Z]:[\\/]+Users[\\/]+[^\\/\s`]+(?:[\\/]|(?=\s|$)))"
    rb"|(?i:\\\\[^\\/\s`]+[\\/]+Users[\\/]+[^\\/\s`]+(?:[\\/]|(?=\s|$)))"
    rb")",
)
CREDENTIAL_RE = re.compile(
    rb"(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)\s*[:=]\s*['\"]?[^\s'\"`]{8,}",
    re.IGNORECASE,
)
PRIVATE_KEY_RE = re.compile(rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")


def manifest(source: Path = ROOT) -> dict:
    return json.loads((source / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))


def tracked_plugin_files(source: Path = ROOT) -> list[Path]:
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "ls-files", "-z", "--", *PLUGIN_PATHS],
        cwd=source,
        check=True,
        capture_output=True,
    )
    files = [Path(raw.decode("utf-8")) for raw in result.stdout.split(b"\0") if raw]
    if Path(".codex-plugin/plugin.json") not in files:
        raise RuntimeError("plugin manifest is not tracked by Git")
    if not any(path.parts and path.parts[0] == "skills" for path in files):
        raise RuntimeError("no tracked skills were found")
    untracked = subprocess.run(
        [
            "git",
            "-c",
            "core.fsmonitor=false",
            "ls-files",
            "-z",
            "--others",
            "--exclude-standard",
            "--",
            *PLUGIN_PATHS,
        ],
        cwd=source,
        check=True,
        capture_output=True,
    )
    untracked_files = [raw.decode("utf-8") for raw in untracked.stdout.split(b"\0") if raw]
    if untracked_files:
        raise RuntimeError(f"untracked files exist under release paths: {', '.join(sorted(untracked_files))}")
    return sorted(files, key=Path.as_posix)


def copy_plugin(destination: Path, source: Path = ROOT) -> None:
    destination.mkdir(parents=True)
    for rel in tracked_plugin_files(source):
        source_path = source / rel
        if any(part.lower() in SENSITIVE_NAMES for part in rel.parts) or rel.suffix.lower() in {".key", ".pem"}:
            raise RuntimeError(f"refusing to package sensitive release path: {rel.as_posix()}")
        if source_path.is_symlink():
            raise RuntimeError(f"refusing to package symbolic link: {rel.as_posix()}")
        if not source_path.is_file():
            raise RuntimeError(f"tracked plugin path is not a regular file: {rel.as_posix()}")
        content = source_path.read_bytes()
        if PRIVATE_KEY_RE.search(content):
            raise RuntimeError(f"refusing to package private key content: {rel.as_posix()}")
        if CREDENTIAL_RE.search(content):
            raise RuntimeError(f"refusing to package possible credential content: {rel.as_posix()}")
        if ABSOLUTE_HOME_RE.search(content):
            raise RuntimeError(f"refusing to package absolute home path: {rel.as_posix()}")
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)


def build_marketplace(output: Path, source: Path = ROOT) -> Path:
    data = manifest(source)
    plugin_root = output / "plugins" / data["name"]
    copy_plugin(plugin_root, source)
    interface = data.get("interface", {})
    display_name = interface.get("displayName", data["name"]) if isinstance(interface, dict) else data["name"]
    catalog = {
        "name": data["name"],
        "interface": {"displayName": display_name},
        "plugins": [
            {
                "name": data["name"],
                "source": {"source": "local", "path": f"./plugins/{data['name']}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Developer Tools",
            }
        ],
    }
    catalog_path = output / ".agents/plugins/marketplace.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    return plugin_root


def archive_tree(source: Path, destination: Path) -> None:
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                paths = sorted(source.rglob("*"), key=lambda path: path.relative_to(source).as_posix())
                for path in paths:
                    if path.is_symlink():
                        raise RuntimeError(f"refusing to archive symbolic link: {path.relative_to(source)}")
                    info = archive.gettarinfo(path, arcname=path.relative_to(source.parent))
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    info.mode = 0o755 if path.is_dir() or path.stat().st_mode & stat.S_IXUSR else 0o644
                    info.pax_headers = {}
                    if path.is_file():
                        with path.open("rb") as handle:
                            archive.addfile(info, handle)
                    else:
                        archive.addfile(info)


def verify(marketplace: Path, plugin_root: Path, source: Path = ROOT) -> None:
    catalog = json.loads((marketplace / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
    entry = catalog["plugins"][0]
    expected = marketplace / entry["source"]["path"]
    if expected.resolve() != plugin_root.resolve():
        raise RuntimeError("marketplace source path does not resolve to packaged plugin")
    packaged = json.loads((plugin_root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    if packaged["name"] != entry["name"]:
        raise RuntimeError("marketplace and plugin names differ")
    packaged_files = {
        path.relative_to(plugin_root)
        for path in plugin_root.rglob("*")
        if path.is_file()
    }
    expected_files = set(tracked_plugin_files(source))
    if packaged_files != expected_files:
        raise RuntimeError("packaged plugin contents differ from the tracked release allowlist")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="build and verify in a temporary directory")
    args = parser.parse_args()
    data = manifest()
    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            marketplace = Path(tmp) / "marketplace"
            plugin_root = build_marketplace(marketplace)
            verify(marketplace, plugin_root)
        print("OK: release marketplace layout")
        return 0

    dist = ROOT / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    marketplace = dist / "marketplace"
    plugin_root = build_marketplace(marketplace)
    verify(marketplace, plugin_root)
    archive = dist / f"{data['name']}-{data['version']}.tar.gz"
    archive_tree(marketplace, archive)
    print(f"Built {marketplace}")
    print(f"Built {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
