#!/usr/bin/env python3
"""End-to-end sequential loop test: two bridged tasks, controller commits, ledger."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "skills" / "cursor-agent-bridge" / "scripts" / "run_cursor_agent.py"
LEDGER = (
    REPO_ROOT
    / "skills"
    / "executing-plans-with-cursor"
    / "scripts"
    / "ledger.py"
)
FAKE_CURSOR = REPO_ROOT / "tests" / "fixtures" / "fake_cursor_agent.py"


class SequentialLoopE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="cursor-e2e-")
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.workspace = Path(self.temp_dir) / "workspace"
        self.workspace.mkdir()
        self.artifact_root = self.workspace / ".superpowers" / "cursor-execution"
        self.ledger = self.artifact_root / "progress.md"
        subprocess.run(
            ["git", "init"], cwd=self.workspace, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.workspace,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "E2E Test"],
            cwd=self.workspace,
            check=True,
            capture_output=True,
        )
        (self.workspace / "README.md").write_text("seed\n")
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=self.workspace,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "seed"],
            cwd=self.workspace,
            check=True,
            capture_output=True,
        )
        self.initial_head = self._head()

    def _head(self) -> str:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.workspace,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _commit(self, paths: list[str], message: str) -> str:
        subprocess.run(
            ["git", "add", *paths],
            cwd=self.workspace,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.workspace,
            check=True,
            capture_output=True,
        )
        return self._head()

    def _dispatch(self, task_id: str, write_file: str, allowed: list[str]) -> dict:
        task_root = self.artifact_root / task_id
        task_root.mkdir(parents=True, exist_ok=True)
        brief = task_root / "brief.md"
        brief.write_text(
            f"# Task {task_id}\n\nAllowed files: {', '.join(allowed)}.\n"
        )
        env = os.environ.copy()
        env.update(
            {
                "FAKE_CURSOR_SCRIPT": str(FAKE_CURSOR),
                "CURSOR_BRIDGE_TEST_HOOK": "1",
                "FAKE_CURSOR_WRITE_FILE": write_file,
                "FAKE_CURSOR_WRITE_REPORT": "1",
                "FAKE_CURSOR_EXIT": "0",
            }
        )
        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--workspace",
                str(self.workspace),
                "--task-brief",
                str(brief),
                "--report",
                str(task_root / "report.md"),
                "--run-record",
                str(task_root / "run-record.json"),
                "--stdout-file",
                str(task_root / "stdout.txt"),
                "--stderr-file",
                str(task_root / "stderr.txt"),
                "--cursor-bin",
                sys.executable,
                *sum((["--allowed-file", a] for a in allowed), []),
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return json.loads((task_root / "run-record.json").read_text())

    def _ledger(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(LEDGER), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_sequential_loop_with_commits_and_ledger(self) -> None:
        result = self._ledger(
            "init",
            str(self.ledger),
            "--branch",
            "agent/e2e",
            "--head",
            self.initial_head,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        record1 = self._dispatch("task-1", "feat-a.txt::alpha", ["feat-a.txt"])
        self.assertEqual(record1["status"], "success")
        self.assertEqual(record1["head_before"], self.initial_head)
        self.assertEqual(record1["head_after"], self.initial_head)
        self.assertEqual(
            record1["changed_files"],
            ["feat-a.txt"],
            "execution artifacts under .superpowers/ must be excluded",
        )
        self.assertEqual(record1["worker_status"], "implemented")
        self.assertEqual(record1["scope_check"], "passed")

        commit1 = self._commit(["feat-a.txt"], "task-1")
        result = self._ledger(
            "set",
            str(self.ledger),
            "--task",
            "task-1",
            "--title",
            "Task one",
            "--status",
            "approved",
            "--worktree",
            str(self.workspace),
            "--artifact-root",
            str(self.artifact_root / "task-1"),
            "--task-commit",
            commit1,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        record2 = self._dispatch("task-2", "feat-b.txt::beta", ["feat-b.txt"])
        self.assertEqual(record2["status"], "success")
        self.assertEqual(
            record2["head_before"],
            commit1,
            "second dispatch must start from the recorded task-1 commit",
        )
        self.assertEqual(record2["changed_files"], ["feat-b.txt"])

        commit2 = self._commit(["feat-b.txt"], "task-2")
        result = self._ledger(
            "set",
            str(self.ledger),
            "--task",
            "task-2",
            "--title",
            "Task two",
            "--status",
            "approved",
            "--task-commit",
            commit2,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        result = self._ledger("validate", str(self.ledger))
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        plan = Path(self.temp_dir) / "plan.yaml"
        plan.write_text(
            "tasks:\n  - id: task-1\n    title: Task one\n  - id: task-2\n    title: Task two\n"
        )
        result = self._ledger("coverage", str(self.ledger), "--plan", str(plan))
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        status = self._ledger("status", str(self.ledger))
        self.assertIn("task-1: approved", status.stdout)
        self.assertIn("task-2: approved", status.stdout)

    def test_coverage_fails_when_plan_task_missing(self) -> None:
        self._ledger(
            "init", str(self.ledger), "--branch", "agent/e2e", "--head", "x"
        )
        plan = Path(self.temp_dir) / "plan.yaml"
        plan.write_text("tasks:\n  - id: task-9\n    title: Missing\n")
        result = self._ledger("coverage", str(self.ledger), "--plan", str(plan))
        self.assertEqual(result.returncode, 1)
        self.assertIn("task-9", result.stderr)

    def test_validate_rejects_bad_status(self) -> None:
        self._ledger(
            "init", str(self.ledger), "--branch", "agent/e2e", "--head", "x"
        )
        self._ledger(
            "set", str(self.ledger), "--task", "task-1", "--status", "approved"
        )
        # Corrupt the status directly to prove validate catches schema drift.
        text = self.ledger.read_text().replace(
            "- Status: approved", "- Status: ship-it"
        )
        self.ledger.write_text(text)
        result = self._ledger("validate", str(self.ledger))
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid status", result.stderr)


if __name__ == "__main__":
    unittest.main()
