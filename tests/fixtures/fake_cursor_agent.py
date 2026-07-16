#!/usr/bin/env python3
"""Fake cursor-agent executable for bridge tests."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
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


def _write_report(report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                "# Task Report",
                "",
                "- Status: `implemented`",
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


def main() -> int:
    exit_code = int(os.environ.get("FAKE_CURSOR_EXIT", "0"))
    write_report = os.environ.get("FAKE_CURSOR_WRITE_REPORT", "1") == "1"
    mutate_head = os.environ.get("FAKE_CURSOR_MUTATE_HEAD", "0") == "1"
    session_id = os.environ.get("FAKE_CURSOR_SESSION_ID", "session-test-123")

    prompt = sys.argv[-1] if len(sys.argv) > 1 else ""
    workspace = None
    for index, arg in enumerate(sys.argv[:-1]):
        if arg == "--workspace" and index + 1 < len(sys.argv) - 1:
            workspace = Path(sys.argv[index + 1])
            break

    report_path = _find_report_path(prompt)
    if write_report and report_path is not None:
        _write_report(report_path)

    if mutate_head and workspace is not None and (workspace / ".git").exists():
        _mutate_head(workspace)

    payload = {"chatId": session_id}
    if os.environ.get("FAKE_CURSOR_PRETTY_JSON", "0") == "1":
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
