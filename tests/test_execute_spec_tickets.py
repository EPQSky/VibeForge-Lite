#!/usr/bin/env python3
"""validate_ticket_gate.py 的正反向测试。"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/execute-spec-tickets/scripts/validate_ticket_gate.py"
TICKET = ".scratch/demo/issues/01-demo.md"
NEXT_TICKET = ".scratch/demo/issues/02-next.md"
STATE = ".scratch/demo/.execute-spec-tickets-state.json"
CRITERIA = ["公开行为可用。", "自动化测试通过。"]
COMPLETED_TICKET = """# 01 — Demo

**Status:** done

- [x] 公开行为可用。
- [x] 自动化测试通过。
"""


class GateScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.external_temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.cmd("git", "init", "-q")
        self.cmd("git", "config", "user.email", "test@example.com")
        self.cmd("git", "config", "user.name", "Test")
        self.write(
            TICKET,
            "# 01 — Demo\n\n**Status:** ready-for-agent\n\n"
            "- [ ] 公开行为可用。\n- [ ] 自动化测试通过。\n",
        )
        self.write(".scratch/demo/spec.md", "# Demo Spec\n")
        self.write(
            NEXT_TICKET,
            "# 02 — Next\n\n**Status:** ready-for-agent\n\n- [ ] 独立后续行为可用。\n",
        )
        self.cmd("git", "add", ".scratch")
        self.cmd("git", "commit", "-qm", "docs: baseline")
        self.base = self.cmd("git", "rev-parse", "HEAD").stdout.strip()
        self.snapshot = self.repo / "snapshot"
        self.snapshot.mkdir()
        self.write(TICKET, COMPLETED_TICKET)
        self.write("demo.py", "VALUE = 1\n")
        self.cmd("git", "add", TICKET, "demo.py")
        self.state = self.valid_state()
        self.save_state()

    def tearDown(self) -> None:
        self.external_temp.cleanup()
        self.temp.cleanup()

    def cmd(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            args,
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"命令失败 {args}: {result.stderr}")
        return result

    def write(self, relative: str, content: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def valid_state(self) -> dict[str, object]:
        return {
            "spec": ".scratch/demo/spec.md",
            "run_id": "test-run",
            "original_head": self.base,
            "current_ticket": TICKET,
            "ticket_review_base": self.base,
            "phase": "ready-to-commit",
            "repair_round": 0,
            "snapshot_dir": str(self.snapshot),
            "preexisting_staged_patch_sha256": hashlib.sha256(b"").hexdigest(),
            "ticket_gate": {
                "implementer": "implementer-1",
                "implementation_audit": {"status": "passed", "evidence": "审计完成"},
                "ownership_check": {"status": "passed", "evidence": "归属已核对"},
                "diff_inspection": {"status": "passed", "evidence": "Diff 已检查"},
                "acceptance": [
                    {"criterion": criterion, "status": "passed", "evidence": f"证据: {criterion}"}
                    for criterion in CRITERIA
                ],
                "verification": [
                    {"name": "pytest", "required": True, "status": "passed", "evidence": "2 passed"}
                ],
                "review_history": [
                    {"reviewer": "reviewer-1", "result": "passed", "evidence": "无阻断问题"}
                ],
                "repair_history": [],
                "preexisting_paths": [],
                "owned_paths": [TICKET, "demo.py"],
                "staged_paths": [TICKET, "demo.py"],
            },
            "completed_commits": [],
            "ticket_results": [],
        }

    def save_state(self) -> None:
        self.write(STATE, json.dumps(self.state, ensure_ascii=False, indent=2))

    def gate(self, phase: str, *extra: str) -> subprocess.CompletedProcess[str]:
        args = ["python3", str(SCRIPT), "--phase", phase, "--ticket", TICKET]
        if phase != "tracker":
            args.extend(["--state", STATE])
        args.extend(extra)
        return self.cmd(*args, check=False)

    def prepare_valid_skip(self) -> None:
        self.cmd("git", "reset", "-q")
        (self.repo / "demo.py").unlink()
        self.write(
            TICKET,
            "# 01 — Demo\n\n**Status:** in-progress\n\n"
            "- [ ] 公开行为可用。\n- [ ] 自动化测试通过。\n",
        )
        archive = Path(self.external_temp.name) / "archive"
        archive.mkdir()
        (archive / "failed.patch").write_text("patch\n", encoding="utf-8")
        (archive / "untracked").mkdir()
        (archive / "recovery.md").write_text("恢复说明\n", encoding="utf-8")
        self.state["phase"] = "repair-exhausted"
        self.state["repair_round"] = 9
        gate = self.state["ticket_gate"]  # type: ignore[assignment]
        gate["review_history"] = [  # type: ignore[index]
            {
                "reviewer": f"reviewer-{index}",
                "result": "blocked",
                "evidence": f"第 {index} 次仍有阻断问题",
            }
            for index in range(1, 11)
        ]
        gate["repair_history"] = [  # type: ignore[index]
            {"round": index, "agent": "implementer-1", "evidence": f"第 {index} 轮修复"}
            for index in range(1, 10)
        ]
        self.state["blocking_findings"] = [
            {
                "severity": "P1",
                "issue": "剩余问题",
                "impact": "incorrect-result",
                "affected_capabilities": ["demo"],
                "evidence": "复审报告",
            }
        ]
        self.state["repair_exhausted_archive"] = {
            "patch": str(archive / "failed.patch"),
            "untracked_backup": str(archive / "untracked"),
            "recovery_instructions": str(archive / "recovery.md"),
        }
        self.state["workspace_isolation"] = {"status": "passed", "evidence": "失败代码已移出"}
        self.state["candidate_assessments"] = [
            {
                "ticket": NEXT_TICKET,
                "depends_on_exhausted": False,
                "impact": "unaffected",
                "eligible": True,
                "evidence": "依赖图和改动路径互不相交",
            }
        ]
        self.state["next_ticket"] = NEXT_TICKET
        self.save_state()

    def test_valid_pre_commit_passes(self) -> None:
        self.assertEqual(self.gate("pre-commit").returncode, 0)

    def test_chinese_legacy_tracker_passes(self) -> None:
        self.write(TICKET, COMPLETED_TICKET.replace("**Status:**", "**状态：**"))
        self.assertEqual(self.gate("tracker").returncode, 0)

    def test_unchecked_acceptance_fails(self) -> None:
        self.write(TICKET, COMPLETED_TICKET.replace("- [x] 自动化", "- [ ] 自动化"))
        self.cmd("git", "add", TICKET)
        result = self.gate("pre-commit")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("未勾选验收项", result.stderr)

    def test_missing_acceptance_evidence_fails(self) -> None:
        self.state["ticket_gate"]["acceptance"].pop()  # type: ignore[index]
        self.save_state()
        result = self.gate("pre-commit")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("逐条精确对应", result.stderr)

    def test_same_reviewer_and_implementer_fails(self) -> None:
        gate = self.state["ticket_gate"]  # type: ignore[assignment]
        gate["review_history"][0]["reviewer"] = "implementer-1"  # type: ignore[index]
        self.save_state()
        result = self.gate("pre-commit")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("不同于实现者", result.stderr)

    def test_staged_scope_mismatch_fails(self) -> None:
        self.write("extra.txt", "unexpected\n")
        self.cmd("git", "add", "extra.txt")
        result = self.gate("pre-commit")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("暂存路径", result.stderr)

    def test_unrecorded_new_file_fails(self) -> None:
        self.write("forgotten.txt", "not staged\n")
        result = self.gate("pre-commit")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("新增变化", result.stderr)

    def test_reviewer_cannot_be_repair_agent(self) -> None:
        self.state["repair_round"] = 1
        gate = self.state["ticket_gate"]  # type: ignore[assignment]
        gate["review_history"] = [  # type: ignore[index]
            {"reviewer": "reviewer-1", "result": "blocked", "evidence": "发现问题"},
            {"reviewer": "reviewer-2", "result": "passed", "evidence": "问题关闭"},
        ]
        gate["repair_history"] = [  # type: ignore[index]
            {"round": 1, "agent": "reviewer-2", "evidence": "修复并验证"}
        ]
        self.save_state()
        result = self.gate("pre-commit")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("修复 Agent", result.stderr)

    def test_more_than_nine_repairs_fails(self) -> None:
        self.state["repair_round"] = 10
        self.save_state()
        result = self.gate("pre-commit")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("0 到 9", result.stderr)

    def test_valid_repair_exhausted_skip_passes(self) -> None:
        self.prepare_valid_skip()
        self.assertEqual(self.gate("skip").returncode, 0)

    def test_skip_rejects_low_impact_blocking_finding(self) -> None:
        self.prepare_valid_skip()
        self.state["blocking_findings"][0]["impact"] = "style"  # type: ignore[index]
        self.save_state()
        result = self.gate("skip")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("错误结果、资源耗尽或验收失败", result.stderr)

    def test_skip_requires_all_later_ticket_assessments(self) -> None:
        self.prepare_valid_skip()
        self.state["candidate_assessments"] = []
        self.state["next_ticket"] = None
        self.save_state()
        result = self.gate("skip")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("覆盖全部后续", result.stderr)

    def test_valid_post_commit_passes(self) -> None:
        self.assertEqual(self.gate("pre-commit").returncode, 0)
        self.cmd("git", "commit", "-qm", "feat: complete ticket 01")
        commit = self.cmd("git", "rev-parse", "HEAD").stdout.strip()
        self.state["phase"] = "committed"
        self.state["ticket_gate"]["commit"] = commit  # type: ignore[index]
        self.state["completed_commits"] = [
            {"ticket": "01", "commit": commit, "repair_rounds": 0, "review": "passed"}
        ]
        self.state["ticket_results"] = [
            {
                "ticket": "01",
                "commit": commit,
                "repair_rounds": 0,
                "review": "passed",
                "ticket_gate": self.state["ticket_gate"],
            }
        ]
        self.save_state()
        self.assertEqual(self.gate("post-commit", "--commit", "HEAD").returncode, 0)

    def test_post_commit_requires_original_staged_patch(self) -> None:
        self.assertEqual(self.gate("pre-commit").returncode, 0)
        self.cmd("git", "commit", "-qm", "feat: complete ticket 01")
        commit = self.cmd("git", "rev-parse", "HEAD").stdout.strip()
        self.write("user-change.txt", "user staged work\n")
        self.cmd("git", "add", "user-change.txt")
        self.state["phase"] = "committed"
        self.state["ticket_gate"]["commit"] = commit  # type: ignore[index]
        self.state["completed_commits"] = [
            {"ticket": "01", "commit": commit, "repair_rounds": 0, "review": "passed"}
        ]
        self.state["ticket_results"] = [
            {
                "ticket": "01",
                "commit": commit,
                "repair_rounds": 0,
                "review": "passed",
                "ticket_gate": self.state["ticket_gate"],
            }
        ]
        self.save_state()
        result = self.gate("post-commit", "--commit", "HEAD")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("暂存补丁", result.stderr)

    def test_post_commit_requires_frozen_ticket_result(self) -> None:
        self.assertEqual(self.gate("pre-commit").returncode, 0)
        self.cmd("git", "commit", "-qm", "feat: complete ticket 01")
        commit = self.cmd("git", "rev-parse", "HEAD").stdout.strip()
        self.state["phase"] = "committed"
        self.state["ticket_gate"]["commit"] = commit  # type: ignore[index]
        self.state["completed_commits"] = [
            {"ticket": "01", "commit": commit, "repair_rounds": 0, "review": "passed"}
        ]
        self.save_state()
        result = self.gate("post-commit", "--commit", "HEAD")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ticket_results", result.stderr)


if __name__ == "__main__":
    unittest.main()
