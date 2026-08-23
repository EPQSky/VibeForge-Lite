from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/vibe-init/scripts/vibe_init.py"


def run(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--target", str(target), "--json", *args],
        text=True,
        capture_output=True,
        check=False,
    )


class VibeInitTests(unittest.TestCase):
    def test_default_is_write_free_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            result = run(target)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["mode"], "dry-run")
            self.assertFalse((target / "AGENTS.md").exists())
            self.assertIn("create", {item["action"] for item in payload["actions"]})

    def test_fresh_apply_then_repeat_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            first = run(target, "--apply")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((target / "AGENTS.md").exists())
            self.assertTrue((target / ".vibecoding/state.json").exists())
            snapshot = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}

            second = run(target, "--apply")
            self.assertEqual(second.returncode, 0, second.stderr)
            payload = json.loads(second.stdout)
            self.assertEqual({item["action"] for item in payload["actions"]}, {"leave unchanged"})
            repeated = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}
            self.assertEqual(snapshot, repeated)

    def test_agents_content_outside_managed_block_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            original = "# Team rules\n\nKeep this exact rule.\n"
            (target / "AGENTS.md").write_text(original, encoding="utf-8")
            result = run(target, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            updated = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertTrue(updated.startswith(original))
            self.assertEqual(updated.count("epq-vibecoding:start"), 1)

    def test_existing_file_mode_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            agents = target / "AGENTS.md"
            agents.write_text("# Existing\n", encoding="utf-8")
            os.chmod(agents, 0o664)
            result = run(target, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(agents.stat().st_mode & 0o777, 0o664)

    def test_unmodified_managed_file_can_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            managed = target / "docs/agents/domain.md"
            managed.parent.mkdir(parents=True)
            old_content = "# Old managed domain guide\n"
            managed.write_text(old_content, encoding="utf-8")
            state_dir = target / ".vibecoding"
            state_dir.mkdir()
            state = {
                "schema_version": 1,
                "template_version": "0.0.1",
                "tracker": "local",
                "managed_files": {
                    "docs/agents/domain.md": hashlib.sha256(old_content.encode()).hexdigest()
                },
            }
            (state_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
            result = run(target, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            actions = json.loads(result.stdout)["actions"]
            self.assertIn("migrate", {item["action"] for item in actions if item["path"] == "docs/agents/domain.md"})
            self.assertNotEqual(managed.read_text(encoding="utf-8"), old_content)

    def test_conflict_stops_all_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            conflict = target / "docs/agents/domain.md"
            conflict.parent.mkdir(parents=True)
            conflict.write_text("# User owned\n", encoding="utf-8")
            result = run(target, "--apply")
            self.assertEqual(result.returncode, 2)
            self.assertFalse((target / "AGENTS.md").exists())
            self.assertFalse((target / ".vibecoding/state.json").exists())
            self.assertEqual(conflict.read_text(encoding="utf-8"), "# User owned\n")

    def test_malformed_agents_markers_are_a_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            agents = target / "AGENTS.md"
            agents.write_text("<!-- epq-vibecoding:start version=old -->\n", encoding="utf-8")
            result = run(target, "--apply")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(agents.read_text(encoding="utf-8"), "<!-- epq-vibecoding:start version=old -->\n")


if __name__ == "__main__":
    unittest.main()
