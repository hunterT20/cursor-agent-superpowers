#!/usr/bin/env python3
"""Deterministic Cursor Agent CLI runner for bounded task execution."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FIXED_MODEL = "composer-2.5[fast=false]"

EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 2
EXIT_CURSOR_FAILURE = 10
EXIT_MISSING_REPORT = 11
EXIT_HEAD_CHANGED = 12


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_head(workspace: Path) -> str | None:
    git_dir = workspace / ".git"
    if not git_dir.exists():
        return None
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _build_fixed_prompt(workspace: Path, task_brief: Path, report_file: Path) -> str:
    return (
        f"Read {task_brief} first; it is the complete binding task contract. "
        f"Implement only that task in the selected workspace at {workspace}. "
        f"Write the full report to {report_file}. "
        "Stop and report ambiguity instead of guessing. "
        "Do not commit, push, merge, rebase, reset, tag, switch, or checkout branches. "
        "Return only a short status after the report is written."
    )


def _session_id_from_payload(payload: dict) -> str | None:
    for key in ("session_id", "sessionId", "chatId"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _extract_session_id(stdout_text: str) -> str | None:
    stripped = stdout_text.strip()
    if stripped:
        try:
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                session_id = _session_id_from_payload(payload)
                if session_id is not None:
                    return session_id
        except json.JSONDecodeError:
            pass

    for line in reversed(stdout_text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            session_id = _session_id_from_payload(payload)
            if session_id is not None:
                return session_id
    return None


def _write_run_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n")


def _invalid_record(
    *,
    exit_code: int,
    status: str,
    workspace: str | None,
    task_brief: str | None,
    report_file: str | None,
    run_record_file: str | None,
    stdout_file: str | None,
    stderr_file: str | None,
    message: str,
) -> dict:
    return {
        "status": status,
        "exit_code": exit_code,
        "cursor_exit_code": None,
        "command": None,
        "workspace": workspace,
        "prompt_file": None,
        "report_file": report_file,
        "stdout_file": stdout_file,
        "stderr_file": stderr_file,
        "head_before": None,
        "head_after": None,
        "head_changed": False,
        "started_at": _utc_now(),
        "finished_at": _utc_now(),
        "session_id": None,
        "message": message,
    }



def _is_dev_fd_path(path: str) -> bool:
    normalized = path.rstrip("/")
    return normalized == "/dev/fd" or normalized.startswith("/dev/fd/")


def _task_brief_validation_error(raw_path: str, task_brief: Path) -> str | None:
    try:
        brief_stat = task_brief.stat()
    except OSError as exc:
        return f"Task brief is not accessible: {task_brief} ({exc})"

    if stat.S_ISFIFO(brief_stat.st_mode):
        return f"Task brief must be a regular file, not a named pipe (FIFO): {task_brief}"
    if not stat.S_ISREG(brief_stat.st_mode):
        return (
            f"Task brief must be a regular file, not a non-regular special file: "
            f"{task_brief}"
        )
    return None


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a bounded Cursor Agent task safely.")
    parser.add_argument("--workspace", required=True, help="Absolute workspace path")
    parser.add_argument("--task-brief", required=True, help="Absolute task brief path")
    parser.add_argument("--report", required=True, help="Absolute report output path")
    parser.add_argument("--run-record", required=True, help="Absolute JSON run-record path")
    parser.add_argument("--stdout-file", required=True, help="Absolute stdout sidecar path")
    parser.add_argument("--stderr-file", required=True, help="Absolute stderr sidecar path")
    parser.add_argument(
        "--cursor-bin",
        default="cursor-agent",
        help="Cursor Agent executable (default: cursor-agent)",
    )
    parser.add_argument(
        "--resume-session",
        default=None,
        help="Optional Cursor session identifier to resume",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    workspace_raw = args.workspace
    task_brief_raw = args.task_brief
    report_raw = args.report
    run_record_raw = args.run_record
    stdout_raw = args.stdout_file
    stderr_raw = args.stderr_file

    path_fields = {
        "workspace": workspace_raw,
        "task_brief": task_brief_raw,
        "report_file": report_raw,
        "run_record_file": run_record_raw,
        "stdout_file": stdout_raw,
        "stderr_file": stderr_raw,
    }

    for label, raw_path in path_fields.items():
        if not Path(raw_path).is_absolute():
            run_record_path = Path(run_record_raw).resolve()
            record = _invalid_record(
                exit_code=EXIT_INVALID_INPUT,
                status="invalid_input",
                workspace=workspace_raw if label != "workspace" else None,
                task_brief=task_brief_raw if label != "task_brief" else None,
                report_file=report_raw if label != "report_file" else None,
                run_record_file=str(run_record_path),
                stdout_file=stdout_raw if label != "stdout_file" else None,
                stderr_file=stderr_raw if label != "stderr_file" else None,
                message=f"{label.replace('_', ' ')} must be an absolute path: {raw_path}",
            )
            _write_run_record(run_record_path, record)
            return EXIT_INVALID_INPUT

    workspace = Path(workspace_raw).resolve()
    task_brief = Path(task_brief_raw).resolve()
    report_file = Path(report_raw).resolve()
    run_record_file = Path(run_record_raw).resolve()
    stdout_file = Path(stdout_raw).resolve()
    stderr_file = Path(stderr_raw).resolve()
    prompt_file = run_record_file.parent / f"{run_record_file.stem}-prompt.txt"

    common = {
        "workspace": str(workspace),
        "task_brief": str(task_brief),
        "report_file": str(report_file),
        "run_record_file": str(run_record_file),
        "stdout_file": str(stdout_file),
        "stderr_file": str(stderr_file),
    }

    if not workspace.is_dir():
        record = _invalid_record(
            exit_code=EXIT_INVALID_INPUT,
            status="invalid_input",
            message=f"Workspace does not exist: {workspace}",
            **common,
        )
        _write_run_record(run_record_file, record)
        return EXIT_INVALID_INPUT

    if _is_dev_fd_path(task_brief_raw):
        record = _invalid_record(
            exit_code=EXIT_INVALID_INPUT,
            status="invalid_input",
            message=(
                f"Task brief must be a durable regular file, not a /dev/fd path "
                f"(process substitution is not allowed): {task_brief_raw}"
            ),
            **common,
        )
        _write_run_record(run_record_file, record)
        return EXIT_INVALID_INPUT

    if _is_dev_fd_path(str(task_brief)):
        record = _invalid_record(
            exit_code=EXIT_INVALID_INPUT,
            status="invalid_input",
            message=(
                f"Task brief must be a durable regular file, not a /dev/fd path "
                f"(process substitution is not allowed): {task_brief}"
            ),
            **common,
        )
        _write_run_record(run_record_file, record)
        return EXIT_INVALID_INPUT

    brief_error = _task_brief_validation_error(task_brief_raw, task_brief)
    if brief_error is not None:
        record = _invalid_record(
            exit_code=EXIT_INVALID_INPUT,
            status="invalid_input",
            message=brief_error,
            **common,
        )
        _write_run_record(run_record_file, record)
        return EXIT_INVALID_INPUT

    if not task_brief.is_file():
        record = _invalid_record(
            exit_code=EXIT_INVALID_INPUT,
            status="invalid_input",
            message=f"Task brief does not exist: {task_brief}",
            **common,
        )
        _write_run_record(run_record_file, record)
        return EXIT_INVALID_INPUT

    started_at = _utc_now()
    head_before = _git_head(workspace)

    fixed_prompt = _build_fixed_prompt(workspace, task_brief, report_file)
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(fixed_prompt + "\n")

    if report_file.exists():
        report_file.unlink()

    cursor_bin = args.cursor_bin
    fake_script = os.environ.get("FAKE_CURSOR_SCRIPT")
    command: list[str]
    if fake_script:
        command = [
            cursor_bin,
            fake_script,
            "--print",
            "--force",
            "--trust",
            "--output-format",
            "json",
            "--model",
            FIXED_MODEL,
            "--workspace",
            str(workspace),
        ]
    else:
        command = [
            cursor_bin,
            "--print",
            "--force",
            "--trust",
            "--output-format",
            "json",
            "--model",
            FIXED_MODEL,
            "--workspace",
            str(workspace),
        ]

    if args.resume_session:
        command.extend(["--resume", args.resume_session])
    command.append(fixed_prompt)

    stdout_file.parent.mkdir(parents=True, exist_ok=True)
    stderr_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        stdout_file.write_text("")
        stderr_file.write_text(str(exc) + "\n")
        head_after = _git_head(workspace)
        head_changed = (
            head_before is not None
            and head_after is not None
            and head_before != head_after
        )
        if head_changed:
            status = "head_changed"
            exit_code = EXIT_HEAD_CHANGED
        else:
            status = "cursor_failure"
            exit_code = EXIT_CURSOR_FAILURE
        record = {
            "status": status,
            "exit_code": exit_code,
            "cursor_exit_code": None,
            "command": command,
            "workspace": str(workspace),
            "prompt_file": str(prompt_file),
            "report_file": str(report_file),
            "stdout_file": str(stdout_file),
            "stderr_file": str(stderr_file),
            "head_before": head_before,
            "head_after": head_after,
            "head_changed": head_changed,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "session_id": None,
        }
        _write_run_record(run_record_file, record)
        return exit_code

    stdout_file.write_text(completed.stdout)
    stderr_file.write_text(completed.stderr)

    head_after = _git_head(workspace)
    head_changed = (
        head_before is not None
        and head_after is not None
        and head_before != head_after
    )
    session_id = _extract_session_id(completed.stdout)

    if head_changed:
        status = "head_changed"
        exit_code = EXIT_HEAD_CHANGED
    elif completed.returncode != 0:
        status = "cursor_failure"
        exit_code = EXIT_CURSOR_FAILURE
    elif not report_file.is_file() or report_file.stat().st_size == 0:
        status = "missing_report"
        exit_code = EXIT_MISSING_REPORT
    else:
        status = "success"
        exit_code = EXIT_SUCCESS

    record = {
        "status": status,
        "exit_code": exit_code,
        "cursor_exit_code": completed.returncode,
        "command": command,
        "workspace": str(workspace),
        "prompt_file": str(prompt_file),
        "report_file": str(report_file),
        "stdout_file": str(stdout_file),
        "stderr_file": str(stderr_file),
        "head_before": head_before,
        "head_after": head_after,
        "head_changed": head_changed,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "session_id": session_id,
    }
    _write_run_record(run_record_file, record)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
