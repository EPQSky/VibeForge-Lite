#!/usr/bin/env python3
"""Build a deterministic local Marketplace and release archive."""

from __future__ import annotations

import argparse
import json
import shutil
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def manifest() -> dict:
    return json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))


def copy_plugin(destination: Path) -> None:
    ignored = shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc", ".DS_Store")
    shutil.copytree(ROOT, destination, ignore=ignored)


def build_marketplace(output: Path) -> Path:
    data = manifest()
    plugin_root = output / "plugins" / data["name"]
    copy_plugin(plugin_root)
    catalog = {
        "name": "epq-vibecoding",
        "interface": {"displayName": "EPQ Vibecoding"},
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
    with tarfile.open(destination, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        for path in sorted(source.rglob("*")):
            info = archive.gettarinfo(path, arcname=path.relative_to(source.parent))
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            if path.is_file():
                with path.open("rb") as handle:
                    archive.addfile(info, handle)
            else:
                archive.addfile(info)


def verify(marketplace: Path, plugin_root: Path) -> None:
    catalog = json.loads((marketplace / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
    entry = catalog["plugins"][0]
    expected = marketplace / entry["source"]["path"]
    if expected.resolve() != plugin_root.resolve():
        raise RuntimeError("marketplace source path does not resolve to packaged plugin")
    packaged = json.loads((plugin_root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    if packaged["name"] != entry["name"]:
        raise RuntimeError("marketplace and plugin names differ")


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
