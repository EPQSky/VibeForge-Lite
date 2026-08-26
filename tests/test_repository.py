from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate_repo.py"
SPEC = importlib.util.spec_from_file_location("validate_repo", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class RepositoryValidationTests(unittest.TestCase):
    def test_repository_is_valid(self) -> None:
        self.assertEqual(VALIDATOR.validate(ROOT), [])

    def test_generated_template_rejects_absolute_home_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "templates/project").mkdir(parents=True)
            (root / "templates/project/AGENTS.md").write_text("read /home/example/secret\n", encoding="utf-8")
            errors = VALIDATOR.portability_errors(root)
            self.assertTrue(any("absolute home path" in error for error in errors))

    def test_generated_template_rejects_windows_home_paths(self) -> None:
        paths = (r"C:\Users\Alice\secret.txt", r"\\server\Users\Alice\secret.txt")
        for absolute_path in paths:
            with self.subTest(absolute_path=absolute_path), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "templates/project").mkdir(parents=True)
                (root / "templates/project/AGENTS.md").write_text(absolute_path, encoding="utf-8")
                errors = VALIDATOR.portability_errors(root)
                self.assertTrue(any("absolute home path" in error for error in errors))

    def test_missing_workflow_is_reported_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__"))
            (root / ".github/workflows/validate.yml").unlink()

            errors = VALIDATOR.validate(root)

            self.assertIn("missing required file: .github/workflows/validate.yml", errors)

    def test_commented_validator_command_does_not_satisfy_ci_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "validate.yml"
            workflow.write_text(
                "jobs:\n"
                "  repository:\n"
                "    steps:\n"
                "      - env:\n"
                "          CODEX_VALIDATOR_COMMIT: 0000000000000000000000000000000000000000\n"
                "        run: |\n"
                "          # curl https://raw.githubusercontent.com/openai/codex/$CODEX_VALIDATOR_COMMIT/validate_plugin.py\n"
                "          # python3 validate_plugin.py .\n",
                encoding="utf-8",
            )

            self.assertTrue(VALIDATOR.workflow_errors(workflow))

    def test_unresolvable_local_source_commit_is_rejected(self) -> None:
        lock = {
            "sources": [
                {
                    "name": "fixture-local-source",
                    "repository": "local",
                    "commit": "0" * 40,
                }
            ]
        }

        errors = VALIDATOR.source_lock_errors(ROOT, lock)

        self.assertTrue(any("commit is not available" in error for error in errors))

    def test_review_contract_includes_uncommitted_and_untracked_work(self) -> None:
        skill = (ROOT / "skills/code-review/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("git diff <review-base>", skill)
        self.assertIn("git ls-files --others --exclude-standard", skill)

    def test_external_tracker_content_is_treated_as_untrusted_data(self) -> None:
        for rel in ("skills/triage/SKILL.md", "skills/to-tickets/SKILL.md"):
            skill = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("untrusted data", skill, rel)

    def test_external_pr_verification_requires_isolation_and_confirmation(self) -> None:
        skill = (ROOT / "skills/triage/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("review the diff statically by default", skill)
        self.assertIn("explicit maintainer confirmation", skill)
        self.assertIn("no credentials", skill)
        self.assertIn("no network access", skill)

    def test_to_spec_has_one_narrow_confirmation_gate(self) -> None:
        skill = (ROOT / "skills/to-spec/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("Do NOT interview the user", skill)
        self.assertIn("single testing-seam confirmation", skill)
        self.assertIn("spec is a parent planning artifact", skill)

    def test_tdd_reuses_previously_approved_seams(self) -> None:
        skill = (ROOT / "skills/tdd/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("approved in the spec or ticket", skill)
        self.assertIn("do not ask again", skill)

    def test_project_local_install_is_the_default(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        skill = (ROOT / "skills/vibe-init/SKILL.md").read_text(encoding="utf-8")
        initializer = (ROOT / "skills/vibe-init/scripts/vibe_init.py").read_text(encoding="utf-8")
        self.assertIn("scripts/install_project.py --target", readme)
        self.assertIn("Project-local installation is the default", skill)
        self.assertIn('default="project"', initializer)
        self.assertIn("--skills plugin", readme)


if __name__ == "__main__":
    unittest.main()
