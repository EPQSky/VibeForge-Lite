from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
