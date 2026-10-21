#!/usr/bin/env python3
"""Fake cursor-agent executable for bridge tests."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


REPORT_PATH_RE = re.compile(
    r"Write the full report to\s+(.+?)\.\s",
    re.IGNORECASE,
)


def _find_report_path(prompt: str) -> Path | None:
    match = REPORT_PATH_RE.search(prompt)
    if not match:
        return None
    return Path(match.group(1).strip())


def _write_report(report_path: Path, status: str = "implemented") -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                "# Task Report",
                "",
                f"- Status: `{status}`",
                "- Summary: fake cursor completed the task.",
                "- Changed files: none",
                "- Tests: none",
                "- Verification: fake run",
                "- Test-first evidence: n/a",
                "- Assumptions: none",
                "- Git prohibition: confirmed",
            ]
        )
        + "\n"
    )


def _mutate_head(workspace: Path) -> None:
    marker = workspace / ".fake-head-mutation.txt"
    marker.write_text("mutation\n")
    subprocess.run(
        ["git", "add", str(marker)],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "fake cursor head mutation"],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )


def _stage_index(workspace: Path) -> None:
    marker = workspace / ".fake-index-mutation.txt"
    marker.write_text("staged\n")
    subprocess.run(
        ["git", "add", str(marker)],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )


def _write_workspace_file(workspace: Path, spec: str) -> None:
    relpath, _, content = spec.partition("::")
    if not relpath:
        return
    target = workspace / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content or "fake cursor output\n")


def _spawn_child(spec: str) -> None:
    marker, _, delay = spec.partition(":")
    if not marker:
        return
    code = (
        "import time,sys;"
        f"time.sleep({float(delay or '2')});"
        f"open({marker!r},'w').write('child alive')"
    )
    subprocess.Popen(
        [sys.executable, "-c", code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    exit_code = int(os.environ.get("FAKE_CURSOR_EXIT", "0"))
    write_report = os.environ.get("FAKE_CURSOR_WRITE_REPORT", "1") == "1"
    mutate_head = os.environ.get("FAKE_CURSOR_MUTATE_HEAD", "0") == "1"
    stage_index = os.environ.get("FAKE_CURSOR_STAGE", "0") == "1"
    session_id = os.environ.get("FAKE_CURSOR_SESSION_ID", "session-test-123")
    session_key = os.environ.get("FAKE_CURSOR_SESSION_KEY", "chatId")
    raw_stdout_hex = os.environ.get("FAKE_CURSOR_RAW_STDOUT", "")
    write_file = os.environ.get("FAKE_CURSOR_WRITE_FILE", "")
    report_status = os.environ.get("FAKE_CURSOR_REPORT_STATUS", "implemented")
    spawn_child = os.environ.get("FAKE_CURSOR_SPAWN_CHILD", "")
    sleep_seconds = float(os.environ.get("FAKE_CURSOR_SLEEP", "0"))

    prompt = sys.argv[-1] if len(sys.argv) > 1 else ""
    workspace = None
    for index, arg in enumerate(sys.argv[:-1]):
        if arg == "--workspace" and index + 1 < len(sys.argv) - 1:
            workspace = Path(sys.argv[index + 1])
            break

    if spawn_child:
        _spawn_child(spawn_child)

    if sleep_seconds > 0:
        time.sleep(sleep_seconds)

    if write_file and workspace is not None:
        _write_workspace_file(workspace, write_file)

    report_path = _find_report_path(prompt)
    if write_report and report_path is not None:
        _write_report(report_path, report_status)

    if mutate_head and workspace is not None and (workspace / ".git").exists():
        _mutate_head(workspace)

    if stage_index and workspace is not None and (workspace / ".git").exists():
        _stage_index(workspace)

    if raw_stdout_hex:
        sys.stdout.buffer.write(bytes.fromhex(raw_stdout_hex))
        sys.stdout.buffer.flush()
    else:
        payload = {session_key: session_id}
        if os.environ.get("FAKE_CURSOR_PRETTY_JSON", "0") == "1":
            print(json.dumps(payload, indent=2))
        else:
            print(json.dumps(payload))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
