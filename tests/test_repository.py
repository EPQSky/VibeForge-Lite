from __future__ import annotations

import importlib.util
import shutil
import tempfile
import tomllib
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

    def test_execute_spec_tickets_limits_blocking_findings(self) -> None:
        skill = (ROOT / "skills/execute-spec-tickets/SKILL.md").read_text(encoding="utf-8")
        for impact in ("incorrect-result", "resource-exhaustion", "acceptance-failure"):
            self.assertIn(impact, skill)
        self.assertIn("不得增加 `repair_round`", skill)
        self.assertIn("理论边角和低影响建议", skill)

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

    def test_mattpocock_source_is_pinned_to_authoritative_release(self) -> None:
        lock = tomllib.loads((ROOT / "UPSTREAM.lock").read_text(encoding="utf-8"))
        source = next(item for item in lock["sources"] if item["name"] == "mattpocock-skills")

        self.assertEqual(source["release_tag"], "v1.2.3")
        self.assertEqual(source["commit"], "6acc160e4e0cd062dbbbd7a1b26ae92855edf07e")
        self.assertEqual(source["reviewed_head"], source["commit"])
        self.assertIn("skills/engineering/codebase-design", source["not_imported"])
        self.assertEqual(lock["skills"]["batch-grill-me"], "mattpocock-skills")
        self.assertNotIn("mattpocock-batch-grill-me", {item["name"] for item in lock["sources"]})

    def test_v123_alignment_keeps_local_workflow_contracts_explicit(self) -> None:
        grilling = (ROOT / "skills/grilling/SKILL.md").read_text(encoding="utf-8")
        guide = (ROOT / "skills/vibe-guide/SKILL.md").read_text(encoding="utf-8")
        phase_boundaries = (ROOT / "skills/vibe-guide/PHASE-BOUNDARIES.md").read_text(encoding="utf-8")

        self.assertIn("Q1 - <question title>", grilling)
        self.assertIn("one at a time", grilling)
        self.assertIn(
            "Q1 - <question title>",
            (ROOT / "skills/batch-grill-me/SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertIn("PHASE-BOUNDARIES.md", guide)
        self.assertIn("Use `$handoff`", phase_boundaries)


if __name__ == "__main__":
    unittest.main()
