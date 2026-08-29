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
INSTALL_SCRIPT = ROOT / "scripts/install_project.py"


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
            self.assertEqual(payload["skills_mode"], "project")
            self.assertFalse((target / "AGENTS.md").exists())
            self.assertIn("create", {item["action"] for item in payload["actions"]})
            self.assertTrue(
                any(item["path"] == ".agents/skills/vibe-init/SKILL.md" for item in payload["actions"])
            )
            self.assertTrue(
                any(
                    item["path"] == ".agents/skills/execute-spec-tickets/SKILL.md"
                    for item in payload["actions"]
                )
            )

    def test_fresh_apply_then_repeat_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            first = run(target, "--apply")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((target / "AGENTS.md").exists())
            self.assertTrue((target / ".vibecoding/state.json").exists())
            self.assertTrue((target / ".agents/skills/vibe-init/SKILL.md").exists())
            self.assertTrue((target / ".agents/skills/execute-spec-tickets/SKILL.md").exists())
            self.assertTrue((target / ".agents/vibeforge-lite/UPSTREAM.lock").exists())
            self.assertTrue((target / ".agents/vibeforge-lite/skill-manifest.json").exists())
            expected_skills = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
            installed_skills = {
                path.parent.name for path in (target / ".agents/skills").glob("*/SKILL.md")
            }
            self.assertEqual(installed_skills, expected_skills)
            state = json.loads((target / ".vibecoding/state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["schema_version"], 2)
            self.assertEqual(state["skills_mode"], "project")
            self.assertIn(".agents/skills/vibe-init/SKILL.md", state["managed_files"])
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
            self.assertEqual(updated.count("vibeforge-lite:start"), 1)

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
            agents.write_text("<!-- legacy-vibecoding:start version=old -->\n", encoding="utf-8")
            result = run(target, "--apply")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(agents.read_text(encoding="utf-8"), "<!-- legacy-vibecoding:start version=old -->\n")

    def test_legacy_managed_block_is_migrated_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            agents = target / "AGENTS.md"
            legacy_namespace = "".join(chr(value) for value in (101, 112, 113)) + "-vibecoding"
            agents.write_text(
                "# Team rules\n\n"
                f"<!-- {legacy_namespace}:start version=0.0.1 -->\n"
                "old managed content\n"
                f"<!-- {legacy_namespace}:end -->\n"
                "\nKeep this exact rule.\n",
                encoding="utf-8",
            )

            result = run(target, "--apply")

            self.assertEqual(result.returncode, 0, result.stderr)
            updated = agents.read_text(encoding="utf-8")
            self.assertIn("<!-- vibeforge-lite:start version=0.3.5 -->", updated)
            self.assertNotIn(legacy_namespace, updated)
            self.assertTrue(updated.endswith("\nKeep this exact rule.\n"))

    def test_mismatched_marker_namespaces_are_a_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            agents = target / "AGENTS.md"
            original = (
                "<!-- alpha-vibecoding:start version=0.0.1 -->\n"
                "user-owned content\n"
                "<!-- beta-vibecoding:end -->\n"
            )
            agents.write_text(original, encoding="utf-8")

            result = run(target, "--apply")

            self.assertEqual(result.returncode, 2)
            self.assertEqual(agents.read_text(encoding="utf-8"), original)

    def test_unknown_matching_marker_namespace_is_a_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            agents = target / "AGENTS.md"
            original = (
                "<!-- another-vibecoding:start version=0.0.1 -->\n"
                "user-owned content\n"
                "<!-- another-vibecoding:end -->\n"
            )
            agents.write_text(original, encoding="utf-8")

            result = run(target, "--apply")

            self.assertEqual(result.returncode, 2)
            self.assertEqual(agents.read_text(encoding="utf-8"), original)

    def test_github_tracker_does_not_create_local_scratch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)

            result = run(target, "--tracker", "github", "--apply")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((target / ".scratch").exists())
            agents = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertNotIn(".scratch/<feature>", agents)
            tracker = (target / "docs/agents/issue-tracker.md").read_text(encoding="utf-8")
            self.assertIn("GitHub Issues as the system of record", tracker)

    def test_plugin_mode_does_not_vendor_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)

            result = run(target, "--skills", "plugin", "--apply")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((target / ".agents").exists())
            agents = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("explicitly selects Plugin mode", agents)
            state = json.loads((target / ".vibecoding/state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["skills_mode"], "plugin")

    def test_non_directory_managed_parent_is_a_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / ".agents").write_text("user-owned file\n", encoding="utf-8")

            result = run(target, "--apply")

            self.assertEqual(result.returncode, 2)
            self.assertEqual((target / ".agents").read_text(encoding="utf-8"), "user-owned file\n")
            conflicts = [
                item for item in json.loads(result.stdout)["actions"] if item["action"] == "conflict"
            ]
            self.assertTrue(any("parent is not a directory" in item["reason"] for item in conflicts))
            self.assertFalse((target / "AGENTS.md").exists())

    def test_directory_at_managed_file_path_is_a_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / ".agents/skills/vibe-guide/SKILL.md").mkdir(parents=True)

            result = run(target, "--apply")

            self.assertEqual(result.returncode, 2)
            conflicts = {
                item["path"] for item in json.loads(result.stdout)["actions"] if item["action"] == "conflict"
            }
            self.assertIn(".agents/skills/vibe-guide/SKILL.md", conflicts)
            self.assertTrue((target / ".agents/skills/vibe-guide/SKILL.md").is_dir())

    def test_unrelated_project_skill_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            custom = target / ".agents/skills/custom/SKILL.md"
            custom.parent.mkdir(parents=True)
            custom.write_text("---\nname: custom\ndescription: Custom\n---\n", encoding="utf-8")
            extra = target / ".agents/skills/vibe-guide/team-notes.md"
            extra.parent.mkdir(parents=True)
            extra.write_text("team-owned notes\n", encoding="utf-8")

            result = run(target, "--apply")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                custom.read_text(encoding="utf-8"),
                "---\nname: custom\ndescription: Custom\n---\n",
            )
            self.assertTrue((target / ".agents/skills/vibe-init/SKILL.md").is_file())
            self.assertEqual(extra.read_text(encoding="utf-8"), "team-owned notes\n")

            vendored_script = target / ".agents/skills/vibe-init/scripts/vibe_init.py"
            repeated = subprocess.run(
                [sys.executable, str(vendored_script), "--target", str(target), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            action_paths = {item["path"] for item in json.loads(repeated.stdout)["actions"]}
            self.assertNotIn(".agents/skills/custom/SKILL.md", action_paths)
            self.assertNotIn(".agents/skills/vibe-guide/team-notes.md", action_paths)
            state = json.loads((target / ".vibecoding/state.json").read_text(encoding="utf-8"))
            self.assertNotIn(".agents/skills/custom/SKILL.md", state["managed_files"])
            self.assertNotIn(".agents/skills/vibe-guide/team-notes.md", state["managed_files"])

    def test_user_modified_vendored_skill_stops_all_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            first = run(target, "--apply")
            self.assertEqual(first.returncode, 0, first.stderr)
            skill = target / ".agents/skills/vibe-guide/SKILL.md"
            skill.write_text("# User-owned override\n", encoding="utf-8")
            state_before = (target / ".vibecoding/state.json").read_bytes()

            second = run(target, "--apply")

            self.assertEqual(second.returncode, 2)
            self.assertEqual(skill.read_text(encoding="utf-8"), "# User-owned override\n")
            self.assertEqual((target / ".vibecoding/state.json").read_bytes(), state_before)
            conflicts = {
                item["path"] for item in json.loads(second.stdout)["actions"] if item["action"] == "conflict"
            }
            self.assertIn(".agents/skills/vibe-guide/SKILL.md", conflicts)

    def test_unmodified_vendored_skill_can_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            skill = target / ".agents/skills/vibe-guide/SKILL.md"
            skill.parent.mkdir(parents=True)
            old_content = "# Old managed skill\n"
            skill.write_text(old_content, encoding="utf-8")
            state_dir = target / ".vibecoding"
            state_dir.mkdir()
            state = {
                "schema_version": 1,
                "template_version": "0.1.0",
                "tracker": "local",
                "managed_files": {
                    ".agents/skills/vibe-guide/SKILL.md": hashlib.sha256(old_content.encode()).hexdigest()
                },
            }
            (state_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

            result = run(target, "--apply")

            self.assertEqual(result.returncode, 0, result.stderr)
            actions = json.loads(result.stdout)["actions"]
            self.assertIn(
                "migrate",
                {item["action"] for item in actions if item["path"] == ".agents/skills/vibe-guide/SKILL.md"},
            )
            self.assertNotEqual(skill.read_text(encoding="utf-8"), old_content)

    def test_vendored_initializer_can_bootstrap_from_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "installed"
            target.mkdir()
            first = run(target, "--apply")
            self.assertEqual(first.returncode, 0, first.stderr)
            vendored_script = target / ".agents/skills/vibe-init/scripts/vibe_init.py"

            second = subprocess.run(
                [sys.executable, str(vendored_script), "--target", str(target), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                {item["action"] for item in json.loads(second.stdout)["actions"]},
                {"leave unchanged"},
            )

    def test_unsafe_vendored_manifest_is_a_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            first = run(target, "--apply")
            self.assertEqual(first.returncode, 0, first.stderr)
            manifest = target / ".agents/vibeforge-lite/skill-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "template_version": "0.3.5",
                        "files": {"../outside": "0" * 64},
                    }
                ),
                encoding="utf-8",
            )
            vendored_script = target / ".agents/skills/vibe-init/scripts/vibe_init.py"

            result = subprocess.run(
                [sys.executable, str(vendored_script), "--target", str(target), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertTrue(
                any(
                    item["action"] == "conflict" and "unsafe entry" in item["reason"]
                    for item in payload["actions"]
                )
            )

    def test_clone_entrypoint_uses_project_install_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)

            result = subprocess.run(
                [sys.executable, str(INSTALL_SCRIPT), "--target", str(target), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["skills_mode"], "project")
            self.assertTrue(
                any(item["path"] == ".agents/skills/vibe-init/SKILL.md" for item in payload["actions"])
            )

    @unittest.skipUnless(hasattr(os, "symlink"), "symbolic links are unavailable")
    def test_symlinked_managed_parent_stops_all_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            target = base / "target"
            outside = base / "outside"
            target.mkdir()
            outside.mkdir()
            os.symlink(outside, target / "docs", target_is_directory=True)

            result = run(target, "--apply")

            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            conflicts = {item["path"] for item in payload["actions"] if item["action"] == "conflict"}
            self.assertIn("docs/agents/domain.md", conflicts)
            self.assertFalse((target / "AGENTS.md").exists())
            self.assertEqual(list(outside.rglob("*")), [])


if __name__ == "__main__":
    unittest.main()
