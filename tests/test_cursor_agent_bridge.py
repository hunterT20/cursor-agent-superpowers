#!/usr/bin/env python3
"""Tests for the cursor-agent-bridge runner."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "skills" / "cursor-agent-bridge" / "scripts" / "run_cursor_agent.py"
FAKE_CURSOR = REPO_ROOT / "tests" / "fixtures" / "fake_cursor_agent.py"
FIXED_MODEL = "composer-2.5[fast=false]"

sys.path.insert(0, str(RUNNER.parent))
from run_cursor_agent import _extract_session_id  # noqa: E402


class CursorAgentBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="cursor-bridge-test-")
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.workspace = Path(self.temp_dir) / "workspace"
        self.workspace.mkdir()
        self.task_brief = Path(self.temp_dir) / "brief.md"
        self.task_brief.write_text("# Task\nDo the thing.\n")
        self.report_file = Path(self.temp_dir) / "report.md"
        self.run_record = Path(self.temp_dir) / "run-record.json"
        self.stdout_file = Path(self.temp_dir) / "stdout.txt"
        self.stderr_file = Path(self.temp_dir) / "stderr.txt"

    def _run_bridge(
        self,
        *,
        workspace: Path | None = None,
        env: dict[str, str] | None = None,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(RUNNER),
            "--workspace",
            str(workspace if workspace is not None else self.workspace),
            "--task-brief",
            str(self.task_brief),
            "--report",
            str(self.report_file),
            "--run-record",
            str(self.run_record),
            "--stdout-file",
            str(self.stdout_file),
            "--stderr-file",
            str(self.stderr_file),
            "--cursor-bin",
            sys.executable,
        ]
        if extra_args:
            command.extend(extra_args)

        run_env = os.environ.copy()
        run_env["FAKE_CURSOR_SCRIPT"] = str(FAKE_CURSOR)
        if env:
            run_env.update(env)
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=run_env,
            check=False,
        )

    def _load_record(self) -> dict:
        return json.loads(self.run_record.read_text())

    def test_rejects_missing_workspace(self) -> None:
        missing_workspace = Path(self.temp_dir) / "missing-workspace"
        result = self._run_bridge(workspace=missing_workspace)
        self.assertEqual(result.returncode, 2)
        record = self._load_record()
        self.assertEqual(record["status"], "invalid_input")
        self.assertEqual(record["exit_code"], 2)

    def test_passes_fixed_model_and_file_paths_without_shell_evaluation(self) -> None:
        sentinel_path = Path(self.temp_dir) / "cursor-bridge-must-not-execute"
        sentinel_payload = f"$(touch {sentinel_path})"
        self.task_brief.write_text(
            "# Task\n"
            f"Run this payload: {sentinel_payload}\n"
            "Also use pipes | and ampersands & in prose.\n"
        )
        env = {
            "FAKE_CURSOR_EXIT": "0",
            "FAKE_CURSOR_WRITE_REPORT": "1",
            "FAKE_CURSOR_MUTATE_HEAD": "0",
            "FAKE_CURSOR_SESSION_ID": "session-test-123",
        }
        result = self._run_bridge(env=env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        record = self._load_record()
        command = record["command"]
        self.assertIsInstance(command, list)
        self.assertIn("--print", command)
        print_index = command.index("--print")
        self.assertEqual(command[print_index + 1], "--force")
        self.assertIn("--model", command)
        self.assertEqual(command[command.index("--model") + 1], FIXED_MODEL)
        self.assertIn("--workspace", command)
        self.assertEqual(command[command.index("--workspace") + 1], str(self.workspace.resolve()))
        prompt = command[-1]
        self.assertIn(str(self.task_brief.resolve()), prompt)
        self.assertIn(str(self.report_file.resolve()), prompt)
        self.assertNotIn("Run this payload:", prompt)
        self.assertNotIn(sentinel_payload, prompt)
        self.assertFalse(sentinel_path.exists())

    def test_rejects_relative_artifact_paths(self) -> None:
        relative_brief = Path("brief.md")
        relative_brief.write_text("# Task\nRelative path test.\n")
        self.addCleanup(relative_brief.unlink, missing_ok=True)

        command = [
            sys.executable,
            str(RUNNER),
            "--workspace",
            str(self.workspace),
            "--task-brief",
            "brief.md",
            "--report",
            str(self.report_file),
            "--run-record",
            str(self.run_record),
            "--stdout-file",
            str(self.stdout_file),
            "--stderr-file",
            str(self.stderr_file),
            "--cursor-bin",
            sys.executable,
        ]
        env = os.environ.copy()
        env["FAKE_CURSOR_SCRIPT"] = str(FAKE_CURSOR)
        result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 2)
        record = self._load_record()
        self.assertEqual(record["status"], "invalid_input")
        self.assertEqual(record["exit_code"], 2)

    def test_supports_paths_with_spaces(self) -> None:
        spaced_dir = Path(self.temp_dir) / "space workspace"
        spaced_dir.mkdir()
        spaced_brief = spaced_dir / "task brief.md"
        spaced_brief.write_text("# Task\nSpace path task.\n")
        spaced_report = spaced_dir / "task report.md"
        spaced_record = spaced_dir / "run record.json"
        spaced_stdout = spaced_dir / "stdout sidecar.txt"
        spaced_stderr = spaced_dir / "stderr sidecar.txt"

        command = [
            sys.executable,
            str(RUNNER),
            "--workspace",
            str(spaced_dir),
            "--task-brief",
            str(spaced_brief),
            "--report",
            str(spaced_report),
            "--run-record",
            str(spaced_record),
            "--stdout-file",
            str(spaced_stdout),
            "--stderr-file",
            str(spaced_stderr),
            "--cursor-bin",
            sys.executable,
        ]
        env = os.environ.copy()
        env.update(
            {
                "FAKE_CURSOR_SCRIPT": str(FAKE_CURSOR),
                "FAKE_CURSOR_EXIT": "0",
                "FAKE_CURSOR_WRITE_REPORT": "1",
                "FAKE_CURSOR_MUTATE_HEAD": "0",
            }
        )
        result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        record = json.loads(spaced_record.read_text())
        self.assertEqual(record["workspace"], str(spaced_dir.resolve()))
        self.assertTrue(spaced_report.exists())
        self.assertGreater(spaced_report.stat().st_size, 0)

    def test_propagates_cursor_failure_as_exit_10(self) -> None:
        env = {
            "FAKE_CURSOR_EXIT": "7",
            "FAKE_CURSOR_WRITE_REPORT": "1",
            "FAKE_CURSOR_MUTATE_HEAD": "0",
        }
        result = self._run_bridge(env=env)
        self.assertEqual(result.returncode, 10)
        record = self._load_record()
        self.assertEqual(record["status"], "cursor_failure")
        self.assertEqual(record["exit_code"], 10)
        self.assertEqual(record["cursor_exit_code"], 7)

    def test_rejects_missing_report_as_exit_11(self) -> None:
        env = {
            "FAKE_CURSOR_EXIT": "0",
            "FAKE_CURSOR_WRITE_REPORT": "0",
            "FAKE_CURSOR_MUTATE_HEAD": "0",
        }
        result = self._run_bridge(env=env)
        self.assertEqual(result.returncode, 11)
        record = self._load_record()
        self.assertEqual(record["status"], "missing_report")
        self.assertEqual(record["exit_code"], 11)

    def test_detects_git_head_change_as_exit_12(self) -> None:
        subprocess.run(["git", "init"], cwd=self.workspace, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.workspace,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Bridge Test"],
            cwd=self.workspace,
            check=True,
            capture_output=True,
        )
        seed = self.workspace / "README.md"
        seed.write_text("seed\n")
        subprocess.run(["git", "add", "README.md"], cwd=self.workspace, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "seed"],
            cwd=self.workspace,
            check=True,
            capture_output=True,
        )

        env = {
            "FAKE_CURSOR_EXIT": "0",
            "FAKE_CURSOR_WRITE_REPORT": "1",
            "FAKE_CURSOR_MUTATE_HEAD": "1",
        }
        result = self._run_bridge(env=env)
        self.assertEqual(result.returncode, 12)
        record = self._load_record()
        self.assertEqual(record["status"], "head_changed")
        self.assertEqual(record["exit_code"], 12)
        self.assertTrue(record["head_changed"])

    def test_succeeds_in_non_git_workspace(self) -> None:
        env = {
            "FAKE_CURSOR_EXIT": "0",
            "FAKE_CURSOR_WRITE_REPORT": "1",
            "FAKE_CURSOR_MUTATE_HEAD": "0",
        }
        result = self._run_bridge(env=env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        record = self._load_record()
        self.assertIsNone(record["head_before"])
        self.assertIsNone(record["head_after"])
        self.assertFalse(record["head_changed"])

    def test_extract_session_id_from_whole_json_session_id_key(self) -> None:
        payload = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "session_id": "e3ddc855-31a9-4ff0-8345-04df3c83291f",
            }
        )
        self.assertEqual(
            _extract_session_id(payload),
            "e3ddc855-31a9-4ff0-8345-04df3c83291f",
        )

    def test_extract_session_id_from_json_lines_session_id_key(self) -> None:
        stdout = "\n".join(
            [
                json.dumps({"type": "progress", "message": "working"}),
                json.dumps(
                    {
                        "type": "result",
                        "subtype": "success",
                        "session_id": "line-session-789",
                    }
                ),
            ]
        )
        self.assertEqual(_extract_session_id(stdout), "line-session-789")

    def test_extract_session_id_prefers_session_id_over_chat_id(self) -> None:
        payload = json.dumps(
            {
                "session_id": "preferred-session",
                "chatId": "legacy-chat",
            }
        )
        self.assertEqual(_extract_session_id(payload), "preferred-session")

    def test_extract_session_id_accepts_session_id_camel_case(self) -> None:
        payload = json.dumps({"sessionId": "camel-session-321"})
        self.assertEqual(_extract_session_id(payload), "camel-session-321")

    def test_extract_session_id_retains_chat_id_compatibility(self) -> None:
        payload = json.dumps({"chatId": "legacy-chat-654"})
        self.assertEqual(_extract_session_id(payload), "legacy-chat-654")

    def test_extract_session_id_ignores_empty_values(self) -> None:
        payload = json.dumps({"session_id": "", "chatId": "fallback-chat"})
        self.assertEqual(_extract_session_id(payload), "fallback-chat")

    def test_captures_real_cursor_session_id_from_json_output(self) -> None:
        env = {
            "FAKE_CURSOR_EXIT": "0",
            "FAKE_CURSOR_WRITE_REPORT": "1",
            "FAKE_CURSOR_MUTATE_HEAD": "0",
            "FAKE_CURSOR_SESSION_ID": "e3ddc855-31a9-4ff0-8345-04df3c83291f",
            "FAKE_CURSOR_SESSION_KEY": "session_id",
        }
        result = self._run_bridge(env=env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        record = self._load_record()
        self.assertEqual(record["session_id"], "e3ddc855-31a9-4ff0-8345-04df3c83291f")

    def test_captures_session_id_from_json_output(self) -> None:
        env = {
            "FAKE_CURSOR_EXIT": "0",
            "FAKE_CURSOR_WRITE_REPORT": "1",
            "FAKE_CURSOR_MUTATE_HEAD": "0",
            "FAKE_CURSOR_SESSION_ID": "session-test-123",
        }
        result = self._run_bridge(env=env, extra_args=["--resume-session", "resume-abc"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        record = self._load_record()
        self.assertEqual(record["session_id"], "session-test-123")
        command = record["command"]
        resume_index = command.index("--resume")
        self.assertEqual(command[resume_index + 1], "resume-abc")

    def test_records_missing_cursor_binary_as_exit_10(self) -> None:
        missing_cursor = Path(self.temp_dir) / "missing-cursor-agent"
        command = [
            sys.executable,
            str(RUNNER),
            "--workspace",
            str(self.workspace),
            "--task-brief",
            str(self.task_brief),
            "--report",
            str(self.report_file),
            "--run-record",
            str(self.run_record),
            "--stdout-file",
            str(self.stdout_file),
            "--stderr-file",
            str(self.stderr_file),
            "--cursor-bin",
            str(missing_cursor),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 10)
        self.assertNotIn("Traceback", result.stderr)
        self.assertTrue(self.run_record.exists())
        self.assertTrue(self.stdout_file.exists())
        self.assertTrue(self.stderr_file.exists())
        record = self._load_record()
        self.assertEqual(record["status"], "cursor_failure")
        self.assertEqual(record["exit_code"], 10)
        self.assertIsNone(record["cursor_exit_code"])

    def test_extracts_session_id_from_pretty_json_output(self) -> None:
        env = {
            "FAKE_CURSOR_EXIT": "0",
            "FAKE_CURSOR_WRITE_REPORT": "1",
            "FAKE_CURSOR_MUTATE_HEAD": "0",
            "FAKE_CURSOR_SESSION_ID": "pretty-session-456",
            "FAKE_CURSOR_PRETTY_JSON": "1",
        }
        result = self._run_bridge(env=env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        record = self._load_record()
        self.assertEqual(record["session_id"], "pretty-session-456")

    def test_skill_forbids_direct_cursor_bypass_under_pressure(self) -> None:
        skill_path = REPO_ROOT / "skills" / "cursor-agent-bridge" / "SKILL.md"
        text = skill_path.read_text()
        lower = text.lower()

        self.assertIn("## hard rule", lower, "SKILL.md must include a Hard rule section")
        self.assertIn("## pressure resistance", lower, "SKILL.md must include a Pressure resistance section")
        self.assertIn("## red flags", lower, "SKILL.md must include a Red flags section")

        self.assertRegex(
            text,
            r"(?is)every\s+.*(?:implementation|fix|dispatch|delegat).*run_cursor_agent\.py",
            "SKILL.md must require every implementation/fix dispatch through run_cursor_agent.py",
        )
        self.assertRegex(
            text,
            r"(?is)never\s+(?:call|invoke|run|use)\s+`?cursor-agent`?\s+direct",
            "SKILL.md must forbid calling cursor-agent directly for a task",
        )
        self.assertRegex(
            text,
            r"(?is)never\s+.*inline.*task",
            "SKILL.md must forbid inlining task contents in the command",
        )
        self.assertRegex(
            text,
            r"(?is)exit\s*0.*(?:not|invocation evidence|does not mean)",
            "SKILL.md must state exit 0 is not task completion",
        )
        self.assertRegex(
            text,
            r"(?is)implemented.*(?:not|invocation evidence|does not mean).*complet",
            "SKILL.md must state implemented status is not task completion",
        )

        for phrase in ("deadline", "one-line", "simple task"):
            self.assertIn(phrase, lower, f"SKILL.md must address pressure scenario: {phrase}")

        self.assertRegex(
            text,
            r"(?is)(?:deadline|one-line|simple task).{0,120}(?:not an exception|no exception|never an exception|not exceptions)",
            "SKILL.md must state deadline/one-line/simple-task pressure is not an exception",
        )

        for phrase in (
            "process substitution",
            "heredoc",
            "printf",
            "echo",
            "/dev/fd",
            "separate prior step",
            "pre-existing",
        ):
            self.assertIn(phrase, lower, f"SKILL.md must forbid inline-brief loophole: {phrase}")

        self.assertRegex(
            text,
            r"(?is)one-line.{0,160}(?:refus|reject|never|must not|do not)",
            "SKILL.md must refuse one-line commands that create and dispatch a brief together",
        )

    def test_rejects_dev_fd_task_brief_path(self) -> None:
        dev_fd_brief = f"/dev/fd/{os.getpid()}"
        command = [
            sys.executable,
            str(RUNNER),
            "--workspace",
            str(self.workspace),
            "--task-brief",
            dev_fd_brief,
            "--report",
            str(self.report_file),
            "--run-record",
            str(self.run_record),
            "--stdout-file",
            str(self.stdout_file),
            "--stderr-file",
            str(self.stderr_file),
            "--cursor-bin",
            sys.executable,
        ]
        env = os.environ.copy()
        env["FAKE_CURSOR_SCRIPT"] = str(FAKE_CURSOR)
        result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 2)
        record = self._load_record()
        self.assertEqual(record["status"], "invalid_input")
        self.assertEqual(record["exit_code"], 2)
        self.assertRegex(record["message"], r"(?i)/dev/fd|process substitution|file descriptor")

    def test_rejects_fifo_task_brief_path(self) -> None:
        fifo_path = Path(self.temp_dir) / "task-brief.pipe"
        os.mkfifo(fifo_path)
        command = [
            sys.executable,
            str(RUNNER),
            "--workspace",
            str(self.workspace),
            "--task-brief",
            str(fifo_path.resolve()),
            "--report",
            str(self.report_file),
            "--run-record",
            str(self.run_record),
            "--stdout-file",
            str(self.stdout_file),
            "--stderr-file",
            str(self.stderr_file),
            "--cursor-bin",
            sys.executable,
        ]
        env = os.environ.copy()
        env["FAKE_CURSOR_SCRIPT"] = str(FAKE_CURSOR)
        result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 2)
        record = self._load_record()
        self.assertEqual(record["status"], "invalid_input")
        self.assertEqual(record["exit_code"], 2)
        self.assertRegex(record["message"], r"(?i)regular file|named pipe|fifo|non-regular")

    def test_accepts_regular_durable_task_brief_file(self) -> None:
        env = {
            "FAKE_CURSOR_EXIT": "0",
            "FAKE_CURSOR_WRITE_REPORT": "1",
            "FAKE_CURSOR_MUTATE_HEAD": "0",
        }
        result = self._run_bridge(env=env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(self.task_brief.is_file())
        self.assertTrue(stat.S_ISREG(self.task_brief.stat().st_mode))


if __name__ == "__main__":
    unittest.main()
