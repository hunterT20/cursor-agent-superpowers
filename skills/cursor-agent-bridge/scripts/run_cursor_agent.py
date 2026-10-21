#!/usr/bin/env python3
"""Deterministic Cursor Agent CLI runner for bounded task execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

FIXED_MODEL = "composer-2.5[fast=false]"

TEST_HOOK_ENV = "CURSOR_BRIDGE_TEST_HOOK"
FAKE_SCRIPT_ENV = "FAKE_CURSOR_SCRIPT"
GIT_COMMAND_TIMEOUT_SECONDS = 30
CURSOR_VERSION_TIMEOUT_SECONDS = 10
DEFAULT_TIMEOUT_SECONDS = 3600
MAX_CHANGED_FILES_RECORDED = 1000
ARTIFACT_PREFIX = ".superpowers/"

EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 2
EXIT_CURSOR_FAILURE = 10
EXIT_MISSING_REPORT = 11
EXIT_HEAD_CHANGED = 12
EXIT_TIMED_OUT = 13
EXIT_SCOPE_VIOLATION = 14
EXIT_WORKER_BLOCKED = 15
EXIT_WORKER_FAILED = 16
EXIT_DISPATCH_LOCKED = 17
EXIT_DIRTY_WORKSPACE = 18

_WORKER_STATUS_RE = re.compile(
    r"^\s*-?\s*status\s*[:=]\s*`?(implemented|blocked|failed)`?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_output(workspace: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=workspace,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _git_state(workspace: Path) -> dict:
    repo_root_raw = _git_output(workspace, "rev-parse", "--show-toplevel")
    repo_root = repo_root_raw.strip() if repo_root_raw else None
    head_raw = _git_output(workspace, "rev-parse", "--verify", "HEAD")
    head = head_raw.strip() if head_raw else None
    index_raw = _git_output(workspace, "ls-files", "--stage")
    index_signature = None
    if repo_root is not None and index_raw is not None:
        index_signature = hashlib.sha256(index_raw.encode("utf-8")).hexdigest()
    return {
        "repo_root": repo_root,
        "head": head,
        "index_signature": index_signature,
    }


def _worktree_changes(workspace: Path) -> set[str] | None:
    """Return repo-relative paths with uncommitted changes, or None if not a repo."""
    status = _git_output(
        workspace, "status", "--porcelain=v1", "-z", "--untracked-files=all"
    )
    if status is None:
        return None
    changed: set[str] = set()
    entries = status.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        if not entry:
            index += 1
            continue
        x, y, path = entry[:1], entry[1:2], entry[3:]
        changed.add(path)
        if x in ("R", "C") or y in ("R", "C"):
            index += 1
            if index < len(entries) and entries[index]:
                changed.add(entries[index])
        index += 1
    return changed


def _cursor_version(cursor_bin: str) -> str | None:
    try:
        result = subprocess.run(
            [cursor_bin, "--version"],
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=CURSOR_VERSION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in (result.stdout or "").splitlines():
        if line.strip():
            return line.strip()
    return None


def _relativize(path: Path, workspace: Path) -> str | None:
    try:
        return path.relative_to(workspace).as_posix()
    except ValueError:
        return None


def _excluded_paths(workspace: Path, artifact_paths: list[Path]) -> set[str]:
    excluded = {
        rel
        for rel in (_relativize(p, workspace) for p in artifact_paths)
        if rel is not None
    }
    return excluded


def _is_excluded(path: str, excluded: set[str]) -> bool:
    return (
        path in excluded
        or path.startswith(ARTIFACT_PREFIX)
        or path == ARTIFACT_PREFIX.rstrip("/")
    )


def _normalize_scope_path(path: str) -> str:
    path = path.lstrip("/")
    while path.startswith("./"):
        path = path[2:]
    return path


def _scope_violations(
    changed: set[str], allowed: list[str], excluded: set[str]
) -> list[str]:
    allowed_files = set()
    allowed_dirs = []
    for entry in allowed:
        normalized = _normalize_scope_path(entry)
        if normalized.endswith("/"):
            allowed_dirs.append(normalized)
        else:
            allowed_files.add(normalized)
    violations = []
    for path in changed:
        normalized = _normalize_scope_path(path)
        if _is_excluded(normalized, excluded):
            continue
        if normalized in allowed_files:
            continue
        if any(normalized.startswith(directory) for directory in allowed_dirs):
            continue
        violations.append(normalized)
    return sorted(violations)


def _worker_status(report_file: Path) -> str | None:
    try:
        text = report_file.read_text(errors="replace")
    except OSError:
        return None
    match = _WORKER_STATUS_RE.search(text)
    return match.group(1).lower() if match else None


def _lock_path(workspace: Path) -> Path:
    digest = hashlib.sha256(str(workspace).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"cursor-bridge-{digest}.lock"


def _kill_process_tree(proc: subprocess.Popen) -> None:
    if hasattr(os, "killpg"):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            return
        except (ProcessLookupError, PermissionError, OSError):
            pass
    proc.kill()


def _build_fixed_prompt(
    workspace: Path, task_brief: Path, report_file: Path, allowed: list[str]
) -> str:
    prompt = (
        f"Read {task_brief} first; it is the complete binding task contract. "
        f"Implement only that task in the selected workspace at {workspace}. "
        f"Write the full report to {report_file}. "
    )
    if allowed:
        prompt += (
            "Only create or modify these workspace-relative files: "
            + ", ".join(allowed)
            + ". "
        )
    prompt += (
        "The report must include a `Status:` line with `implemented`, "
        "`blocked`, or `failed`. "
        "Stop and report ambiguity instead of guessing. "
        "Do not commit, push, merge, rebase, reset, tag, switch, or checkout branches. "
        "Return only a short status after the report is written."
    )
    return prompt


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
    """Atomically write the run record: temp file + rename, so readers never
    see a half-written record. Record existence is the completion signal."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        tmp.write_text(json.dumps(record, indent=2) + "\n")
        os.replace(tmp, path)
    except OSError as exc:
        print(
            f"run_cursor_agent: unable to write run record {path}: {exc}",
            file=sys.stderr,
        )


def _early_record(
    *,
    exit_code: int,
    status: str,
    message: str,
    common: dict,
) -> dict:
    record = {
        "status": status,
        "exit_code": exit_code,
        "cursor_exit_code": None,
        "command": None,
        "workspace": None,
        "controller_cwd": None,
        "cursor_cwd": None,
        "repo_root": None,
        "cursor_version": None,
        "test_hook": False,
        "timed_out": False,
        "task_brief": None,
        "prompt_file": None,
        "report_file": None,
        "stdout_file": None,
        "stderr_file": None,
        "lock_file": None,
        "head_before": None,
        "head_after": None,
        "head_changed": False,
        "index_changed": False,
        "changed_files": None,
        "scope_check": "not_configured",
        "scope_violated_files": [],
        "worker_status": None,
        "notify_command": None,
        "started_at": _utc_now(),
        "finished_at": _utc_now(),
        "session_id": None,
        "message": message,
    }
    record.update(common)
    return record


def _run_notify(command: str, record_path: Path, record: dict) -> None:
    """Best-effort completion callback; failures never change the exit code."""
    if not command:
        return
    env = os.environ.copy()
    env.update(
        {
            "CURSOR_RUN_RECORD": str(record_path),
            "CURSOR_EXIT_CODE": str(record["exit_code"]),
            "CURSOR_STATUS": str(record["status"]),
            "CURSOR_WORKSPACE": str(record.get("workspace") or ""),
        }
    )
    try:
        subprocess.run(
            command,
            shell=True,
            env=env,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"run_cursor_agent: notify command failed: {exc}", file=sys.stderr)


def _is_dev_fd_path(path: str) -> bool:
    normalized = path.rstrip("/")
    return normalized == "/dev/fd" or normalized.startswith("/dev/fd/")


def _task_brief_validation_error(task_brief: Path) -> str | None:
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
    if brief_stat.st_size == 0:
        return f"Task brief must be a non-empty file: {task_brief}"
    if not os.access(task_brief, os.R_OK):
        return f"Task brief is not readable: {task_brief}"
    return None


def _output_path_error(path: Path) -> str | None:
    try:
        path_stat = path.stat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        return f"Artifact path is not accessible: {path} ({exc})"
    if not stat.S_ISREG(path_stat.st_mode):
        return (
            "Artifact path must not be an existing non-regular path "
            f"(directory, FIFO, socket, or device): {path}"
        )
    return None


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=(
            "Maximum seconds to wait for the Cursor run before killing its "
            f"process group (default: {DEFAULT_TIMEOUT_SECONDS}; 0 disables)"
        ),
    )
    parser.add_argument(
        "--allowed-file",
        action="append",
        default=None,
        help=(
            "Workspace-relative file the worker may create or modify; repeat for "
            "each allowed file. A trailing '/' allows everything under that "
            "directory. When given, worker file changes outside the list fail "
            "with exit 14."
        ),
    )
    parser.add_argument(
        "--expect-clean",
        action="store_true",
        help=(
            "Refuse to dispatch unless the workspace has no uncommitted changes "
            "outside .superpowers/ and the artifact paths (exit 18 otherwise)."
        ),
    )
    parser.add_argument(
        "--notify-command",
        default=None,
        help=(
            "Optional controller-provided shell command run once after the run "
            "record is written (push notification). Receives CURSOR_RUN_RECORD, "
            "CURSOR_EXIT_CODE, CURSOR_STATUS, CURSOR_WORKSPACE env vars; "
            "failures are logged to stderr and never change the exit code."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

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
            record = _early_record(
                exit_code=EXIT_INVALID_INPUT,
                status="invalid_input",
                common={
                    "workspace": workspace_raw if label != "workspace" else None,
                    "task_brief": task_brief_raw if label != "task_brief" else None,
                    "report_file": report_raw if label != "report_file" else None,
                    "stdout_file": stdout_raw if label != "stdout_file" else None,
                    "stderr_file": stderr_raw if label != "stderr_file" else None,
                },
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

    controller_cwd = str(Path.cwd().resolve())
    cursor_version = _cursor_version(args.cursor_bin)
    test_hook = os.environ.get(TEST_HOOK_ENV) == "1"

    common = {
        "workspace": str(workspace),
        "controller_cwd": controller_cwd,
        "cursor_cwd": str(workspace),
        "cursor_version": cursor_version,
        "test_hook": test_hook,
        "task_brief": str(task_brief),
        "prompt_file": str(prompt_file),
        "report_file": str(report_file),
        "stdout_file": str(stdout_file),
        "stderr_file": str(stderr_file),
    }

    common["notify_command"] = args.notify_command

    def _early(status: str, exit_code: int, message: str) -> int:
        record = _early_record(
            exit_code=exit_code,
            status=status,
            common=common,
            message=message,
        )
        _write_run_record(run_record_file, record)
        _run_notify(args.notify_command, run_record_file, record)
        return exit_code

    if not workspace.is_dir():
        return _early(
            "invalid_input",
            EXIT_INVALID_INPUT,
            f"Workspace does not exist: {workspace}",
        )

    if _is_dev_fd_path(task_brief_raw) or _is_dev_fd_path(str(task_brief)):
        return _early(
            "invalid_input",
            EXIT_INVALID_INPUT,
            f"Task brief must be a durable regular file, not a /dev/fd path "
            f"(process substitution is not allowed): {task_brief_raw}",
        )

    brief_error = _task_brief_validation_error(task_brief)
    if brief_error is not None:
        return _early("invalid_input", EXIT_INVALID_INPUT, brief_error)

    artifact_paths = {
        "task brief": task_brief,
        "report": report_file,
        "run record": run_record_file,
        "stdout": stdout_file,
        "stderr": stderr_file,
        "prompt": prompt_file,
    }
    seen: dict[Path, str] = {}
    for label, artifact_path in artifact_paths.items():
        if artifact_path in seen:
            return _early(
                "invalid_input",
                EXIT_INVALID_INPUT,
                f"Artifact paths must be distinct after resolution: "
                f"{label} and {seen[artifact_path]} both resolve to {artifact_path}",
            )
        seen[artifact_path] = label

    for label, artifact_path in artifact_paths.items():
        if label == "task brief":
            continue
        output_error = _output_path_error(artifact_path)
        if output_error is not None:
            return _early("invalid_input", EXIT_INVALID_INPUT, output_error)

    excluded = _excluded_paths(workspace, list(artifact_paths.values()))
    lock_file = _lock_path(workspace)
    common["lock_file"] = str(lock_file)

    try:
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            holder = lock_file.read_text(errors="replace").strip()
        except OSError:
            holder = "unreadable"
        return _early(
            "dispatch_locked",
            EXIT_DISPATCH_LOCKED,
            f"Another dispatch holds the workspace lock {lock_file}: {holder}",
        )
    except OSError as exc:
        return _early(
            "dispatch_locked",
            EXIT_DISPATCH_LOCKED,
            f"Cannot create workspace lock {lock_file}: {exc}",
        )

    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(
                {
                    "pid": os.getpid(),
                    "workspace": str(workspace),
                    "run_record": str(run_record_file),
                    "started_at": _utc_now(),
                },
                handle,
            )

        started_at = _utc_now()
        git_before = _git_state(workspace)
        head_before = git_before["head"]
        index_before = git_before["index_signature"]
        changes_before = (
            _worktree_changes(workspace)
            if git_before["repo_root"] is not None
            else None
        )

        if args.expect_clean:
            if changes_before is None:
                return _early(
                    "dirty_workspace",
                    EXIT_DIRTY_WORKSPACE,
                    "--expect-clean requires a git workspace; cannot verify clean "
                    f"state in {workspace}",
                )
            dirty = sorted(
                p for p in changes_before if not _is_excluded(p, excluded)
            )
            if dirty:
                return _early(
                    "dirty_workspace",
                    EXIT_DIRTY_WORKSPACE,
                    "Workspace has uncommitted changes outside .superpowers/ and "
                    f"artifact paths: {', '.join(dirty[:20])}",
                )

        allowed = args.allowed_file or []
        fixed_prompt = _build_fixed_prompt(workspace, task_brief, report_file, allowed)
        try:
            prompt_file.parent.mkdir(parents=True, exist_ok=True)
            prompt_file.write_text(fixed_prompt + "\n")
        except OSError as exc:
            return _early(
                "invalid_input",
                EXIT_INVALID_INPUT,
                f"Cannot write prompt file {prompt_file}: {exc}",
            )

        if report_file.exists():
            try:
                report_file.unlink()
            except OSError as exc:
                return _early(
                    "invalid_input",
                    EXIT_INVALID_INPUT,
                    f"Cannot remove stale report {report_file}: {exc}",
                )

        cursor_bin = args.cursor_bin
        fake_script = os.environ.get(FAKE_SCRIPT_ENV) if test_hook else None
        command: list[str] = [cursor_bin]
        if fake_script:
            command.append(fake_script)
        command.extend(
            [
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
        )

        if args.resume_session:
            command.extend(["--resume", args.resume_session])
        command.append(fixed_prompt)

        try:
            stdout_file.parent.mkdir(parents=True, exist_ok=True)
            stderr_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return _early(
                "invalid_input",
                EXIT_INVALID_INPUT,
                f"Cannot create sidecar directories: {exc}",
            )

        timeout_seconds = args.timeout if args.timeout and args.timeout > 0 else None
        timed_out = False
        spawn_failed = False
        cursor_rc: int | None = None
        stdout_text = ""
        stderr_text = ""

        try:
            # Cursor discovers project config from process cwd. Keep the
            # controller's repo (which may have an unrelated .cursor/cli.json)
            # out of the worker invocation and run in the selected workspace.
            # start_new_session puts the child in its own process group so a
            # timeout can kill the whole tree it spawned.
            proc = subprocess.Popen(
                command,
                cwd=workspace,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                start_new_session=True,
            )
        except OSError as exc:
            spawn_failed = True
            stderr_text = str(exc) + "\n"

        if not spawn_failed:
            try:
                stdout_text, stderr_text = proc.communicate(timeout=timeout_seconds)
                cursor_rc = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_process_tree(proc)
                out, err = proc.communicate()
                stdout_text = _as_text(out)
                stderr_text = _as_text(err)
                cursor_rc = proc.returncode

        try:
            stdout_file.write_text(stdout_text)
            stderr_file.write_text(stderr_text)
        except OSError as exc:
            print(
                f"run_cursor_agent: unable to write sidecar output: {exc}",
                file=sys.stderr,
            )

        git_after = _git_state(workspace)
        head_after = git_after["head"]
        index_after = git_after["index_signature"]
        head_changed = head_before != head_after
        index_changed = index_before != index_after
        session_id = _extract_session_id(stdout_text)

        changes_after = (
            _worktree_changes(workspace)
            if git_after["repo_root"] is not None
            else None
        )
        changed_files: list[str] | None = None
        if changes_before is not None and changes_after is not None:
            changed_files = sorted(
                path
                for path in changes_after - changes_before
                if not _is_excluded(_normalize_scope_path(path), excluded)
            )

        scope_check = "not_configured"
        scope_violated: list[str] = []
        if allowed:
            if changed_files is None:
                scope_check = "skipped_non_git"
            else:
                scope_violated = _scope_violations(
                    set(changed_files), allowed, excluded
                )
                scope_check = "failed" if scope_violated else "passed"

        report_exists = report_file.is_file() and report_file.stat().st_size > 0
        worker_status = _worker_status(report_file) if report_exists else None

        if head_changed:
            status = "head_changed"
            exit_code = EXIT_HEAD_CHANGED
        elif index_changed:
            status = "index_changed"
            exit_code = EXIT_HEAD_CHANGED
        elif timed_out:
            status = "timed_out"
            exit_code = EXIT_TIMED_OUT
        elif spawn_failed or cursor_rc != 0:
            status = "cursor_failure"
            exit_code = EXIT_CURSOR_FAILURE
        elif not report_exists:
            status = "missing_report"
            exit_code = EXIT_MISSING_REPORT
        elif worker_status == "blocked":
            status = "worker_blocked"
            exit_code = EXIT_WORKER_BLOCKED
        elif worker_status == "failed":
            status = "worker_failed"
            exit_code = EXIT_WORKER_FAILED
        elif scope_violated:
            status = "scope_violation"
            exit_code = EXIT_SCOPE_VIOLATION
        else:
            status = "success"
            exit_code = EXIT_SUCCESS

        record = {
            "status": status,
            "exit_code": exit_code,
            "cursor_exit_code": cursor_rc,
            "command": command,
            "workspace": str(workspace),
            "controller_cwd": controller_cwd,
            "cursor_cwd": str(workspace),
            "repo_root": git_before["repo_root"],
            "cursor_version": cursor_version,
            "test_hook": test_hook,
            "timed_out": timed_out,
            "task_brief": str(task_brief),
            "prompt_file": str(prompt_file),
            "report_file": str(report_file),
            "stdout_file": str(stdout_file),
            "stderr_file": str(stderr_file),
            "lock_file": str(lock_file),
            "head_before": head_before,
            "head_after": head_after,
            "head_changed": head_changed,
            "index_changed": index_changed,
            "changed_files": (
                changed_files[:MAX_CHANGED_FILES_RECORDED]
                if changed_files is not None
                else None
            ),
            "scope_check": scope_check,
            "scope_violated_files": scope_violated,
            "worker_status": worker_status,
            "notify_command": args.notify_command,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "session_id": session_id,
        }
        _write_run_record(run_record_file, record)
        _run_notify(args.notify_command, run_record_file, record)
        return exit_code
    finally:
        try:
            lock_file.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
