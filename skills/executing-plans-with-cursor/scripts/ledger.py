#!/usr/bin/env python3
"""Authoritative integration ledger helper for cursor-execution progress.md.

Usage:
  ledger.py init FILE --branch NAME [--head SHA]
  ledger.py set FILE --task ID [--title T] [--status S] [--branch B]
              [--worktree P] [--artifact-root P] [--wave-base-head SHA]
              [--session ID] [--review-state S] [--task-commit SHA]
              [--integrated-head SHA] [--brief P] [--report P] [--notes TEXT]
  ledger.py validate FILE
  ledger.py status FILE
  ledger.py coverage FILE --plan PLAN.yaml

Exit codes: 0 success, 1 validation/coverage failure, 2 usage error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CANONICAL_FIELDS = [
    "Status",
    "Branch",
    "Worktree path",
    "Artifact root",
    "Wave-base HEAD",
    "Session ID",
    "Review state",
    "Task commit SHA",
    "Integrated HEAD",
    "Brief",
    "Report",
    "Notes",
]

STATUSES = {
    "pending",
    "in-review",
    "fix-required",
    "approved-isolated",
    "approved",
    "blocked",
    "failed",
}

TASK_HEADING_RE = re.compile(r"^##\s+Task\s+(\S+):\s*(.*)$")
FIELD_RE = re.compile(r"^-\s+([^:]+):\s*(.*)$")
PLAN_ID_RE = re.compile(r"^\s*-\s+id:\s*([^\s#]+)\s*$", re.MULTILINE)

ARG_TO_FIELD = {
    "status": "Status",
    "branch": "Branch",
    "worktree": "Worktree path",
    "artifact_root": "Artifact root",
    "wave_base_head": "Wave-base HEAD",
    "session": "Session ID",
    "review_state": "Review state",
    "task_commit": "Task commit SHA",
    "integrated_head": "Integrated HEAD",
    "brief": "Brief",
    "report": "Report",
    "notes": "Notes",
}


def _fail(message: str) -> int:
    print(f"ledger: {message}", file=sys.stderr)
    return 1


def _parse_ledger(text: str) -> tuple[str, list[dict]]:
    """Split a progress.md into (header_text, [task dicts])."""
    header_lines: list[str] = []
    tasks: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        task_match = TASK_HEADING_RE.match(line)
        if task_match:
            current = {
                "id": task_match.group(1),
                "title": task_match.group(2).strip(),
                "fields": {},
                "extra_lines": [],
            }
            tasks.append(current)
            continue
        if current is None:
            header_lines.append(line)
            continue
        field_match = FIELD_RE.match(line)
        if field_match:
            current["fields"][field_match.group(1).strip()] = field_match.group(
                2
            ).strip()
        elif line.strip():
            current["extra_lines"].append(line)
    return "\n".join(header_lines).rstrip(), tasks


def _render_ledger(header: str, tasks: list[dict]) -> str:
    chunks = [header, ""]
    for task in tasks:
        title = task["title"] or "untitled"
        chunks.append(f"## Task {task['id']}: {title}")
        for field in CANONICAL_FIELDS:
            value = task["fields"].get(field)
            if value is not None:
                chunks.append(f"- {field}: {value}")
        for field, value in task["fields"].items():
            if field not in CANONICAL_FIELDS:
                chunks.append(f"- {field}: {value}")
        for line in task["extra_lines"]:
            chunks.append(line)
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def _validate(text: str) -> list[str]:
    header, tasks = _parse_ledger(text)
    errors: list[str] = []
    if "Integration branch:" not in header:
        errors.append("missing 'Integration branch:' in header")
    if "Starting HEAD:" not in header:
        errors.append("missing 'Starting HEAD:' in header")
    seen_ids: set[str] = set()
    for task in tasks:
        task_id = task["id"]
        if task_id in seen_ids:
            errors.append(f"task {task_id}: duplicate task id")
        seen_ids.add(task_id)
        if not task["title"]:
            errors.append(f"task {task_id}: missing title")
        for field in CANONICAL_FIELDS:
            if field not in task["fields"]:
                errors.append(f"task {task_id}: missing field '{field}'")
        status = task["fields"].get("Status", "")
        if status and status not in STATUSES:
            errors.append(
                f"task {task_id}: invalid status '{status}' "
                f"(expected one of: {', '.join(sorted(STATUSES))})"
            )
    return errors


def _cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if path.exists():
        return _fail(f"refusing to overwrite existing ledger: {path}")
    header = (
        "# Cursor Execution Progress\n\n"
        f"Integration branch: `{args.branch}`\n"
        f"Starting HEAD: `{args.head or 'none'}`"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_ledger(header, []))
    print(f"ledger: initialized {path}")
    return 0


def _cmd_set(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.is_file():
        return _fail(f"ledger not found: {path} (run init first)")
    header, tasks = _parse_ledger(path.read_text())
    task = next((t for t in tasks if t["id"] == args.task), None)
    if task is None:
        task = {
            "id": args.task,
            "title": args.title or "",
            "fields": {field: "none" for field in CANONICAL_FIELDS},
            "extra_lines": [],
        }
        tasks.append(task)
    if args.title:
        task["title"] = args.title
    for arg_name, field in ARG_TO_FIELD.items():
        value = getattr(args, arg_name, None)
        if value is not None:
            task["fields"][field] = value
    path.write_text(_render_ledger(header, tasks))
    print(f"ledger: updated task {args.task} in {path}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.is_file():
        return _fail(f"ledger not found: {path}")
    errors = _validate(path.read_text())
    if errors:
        for error in errors:
            print(f"ledger: {error}", file=sys.stderr)
        return 1
    print(f"ledger: {path} is valid")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.is_file():
        return _fail(f"ledger not found: {path}")
    _, tasks = _parse_ledger(path.read_text())
    if not tasks:
        print("ledger: no tasks recorded")
        return 0
    for task in tasks:
        status = task["fields"].get("Status", "?")
        print(f"{task['id']}: {status}")
    return 0


def _cmd_coverage(args: argparse.Namespace) -> int:
    path = Path(args.file)
    plan_path = Path(args.plan)
    if not path.is_file():
        return _fail(f"ledger not found: {path}")
    if not plan_path.is_file():
        return _fail(f"plan not found: {plan_path}")
    plan_ids = PLAN_ID_RE.findall(plan_path.read_text())
    if not plan_ids:
        return _fail(f"no '- id: <task-id>' entries found in {plan_path}")
    _, tasks = _parse_ledger(path.read_text())
    ledger_ids = {task["id"] for task in tasks}
    missing = [task_id for task_id in plan_ids if task_id not in ledger_ids]
    extra = [task["id"] for task in tasks if task["id"] not in plan_ids]
    for task_id in extra:
        print(
            f"ledger: warning: task {task_id} is in the ledger but not in the plan",
            file=sys.stderr,
        )
    if missing:
        print(
            f"ledger: plan tasks missing from ledger: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1
    print(f"ledger: all {len(plan_ids)} plan tasks have ledger entries")
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage the authoritative cursor-execution progress ledger."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a fresh ledger")
    init.add_argument("file")
    init.add_argument("--branch", required=True)
    init.add_argument("--head", default=None)
    init.set_defaults(func=_cmd_init)

    set_cmd = sub.add_parser("set", help="Create or update a task entry")
    set_cmd.add_argument("file")
    set_cmd.add_argument("--task", required=True)
    set_cmd.add_argument("--title", default=None)
    for arg_name in ARG_TO_FIELD:
        set_cmd.add_argument(f"--{arg_name.replace('_', '-')}", default=None)
    set_cmd.set_defaults(func=_cmd_set)

    validate = sub.add_parser("validate", help="Check ledger schema")
    validate.add_argument("file")
    validate.set_defaults(func=_cmd_validate)

    status = sub.add_parser("status", help="Print task status summary")
    status.add_argument("file")
    status.set_defaults(func=_cmd_status)

    coverage = sub.add_parser(
        "coverage", help="Verify every plan task has a ledger entry"
    )
    coverage.add_argument("file")
    coverage.add_argument("--plan", required=True)
    coverage.set_defaults(func=_cmd_coverage)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
