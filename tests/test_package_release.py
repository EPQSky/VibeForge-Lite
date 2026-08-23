from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "scripts/package_release.py"
SPEC = importlib.util.spec_from_file_location("package_release", PACKAGE_PATH)
assert SPEC and SPEC.loader
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


def create_source(root: Path) -> None:
    manifest = root / ".codex-plugin/plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"name": "fixture-plugin", "version": "1.0.0"}),
        encoding="utf-8",
    )
    skill = root / "skills/example/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: example\ndescription: Fixture\n---\n", encoding="utf-8")
    (root / "LICENSE").write_text("fixture license\n", encoding="utf-8")
    subprocess.run(["git", "-c", "core.fsmonitor=false", "init", "-q", str(root)], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(root),
            "add",
            ".codex-plugin/plugin.json",
            "skills/example/SKILL.md",
            "LICENSE",
        ],
        check=True,
    )


class PackageReleaseTests(unittest.TestCase):
    def test_untracked_files_are_not_packaged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            create_source(source)
            (source / ".env").write_text("SECRET=do-not-package\n", encoding="utf-8")

            plugin_root = PACKAGE.build_marketplace(base / "marketplace", source)

            self.assertTrue((plugin_root / ".codex-plugin/plugin.json").exists())
            self.assertFalse((plugin_root / ".env").exists())

    def test_tracked_sensitive_files_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            create_source(source)
            secret = source / "skills/example/.env"
            secret.write_text("API_KEY=fixture-value\n", encoding="utf-8")
            subprocess.run(
                ["git", "-c", "core.fsmonitor=false", "-C", str(source), "add", "skills/example/.env"],
                check=True,
            )

            with self.assertRaisesRegex(RuntimeError, "sensitive release path"):
                PACKAGE.build_marketplace(Path(tmp) / "marketplace", source)

    def test_tracked_credential_content_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            create_source(source)
            config = source / "skills/example/config.txt"
            config.write_text("api_key = 'fixture-secret-value'\n", encoding="utf-8")
            subprocess.run(
                ["git", "-c", "core.fsmonitor=false", "-C", str(source), "add", "skills/example/config.txt"],
                check=True,
            )

            with self.assertRaisesRegex(RuntimeError, "possible credential content"):
                PACKAGE.build_marketplace(Path(tmp) / "marketplace", source)

    def test_tracked_windows_home_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            create_source(source)
            config = source / "skills/example/local-path.txt"
            config.write_text(r"C:\Users\Alice\secret.txt", encoding="utf-8")
            subprocess.run(
                ["git", "-c", "core.fsmonitor=false", "-C", str(source), "add", "skills/example/local-path.txt"],
                check=True,
            )

            with self.assertRaisesRegex(RuntimeError, "absolute home path"):
                PACKAGE.build_marketplace(Path(tmp) / "marketplace", source)

    def test_release_archive_is_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            create_source(source)
            marketplace = base / "marketplace"
            PACKAGE.build_marketplace(marketplace, source)
            first = base / "first.tar.gz"
            second = base / "second.tar.gz"

            PACKAGE.archive_tree(marketplace, first)
            time.sleep(1.1)
            PACKAGE.archive_tree(marketplace, second)

            self.assertEqual(int.from_bytes(first.read_bytes()[4:8], "little"), 0)
            self.assertEqual(hashlib.sha256(first.read_bytes()).digest(), hashlib.sha256(second.read_bytes()).digest())


if __name__ == "__main__":
    unittest.main()
