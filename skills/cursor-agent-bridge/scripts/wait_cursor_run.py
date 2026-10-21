#!/usr/bin/env python3
"""Blocking wait for one or more cursor-bridge run records.

The orchestrator calls this once instead of polling the run state and burning
tokens: the process sleeps until every record exists, then prints each
record's status and exits.

Usage:
  wait_cursor_run.py RECORD.json [RECORD2.json ...] [--interval SEC] [--timeout SEC]

Exit codes:
  0    every record exists, parses, and reports exit_code 0
  N    first nonzero exit_code among the records (worker/run failures surface)
  2    usage error
  124  --timeout elapsed before all records appeared
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

EXIT_TIMEOUT = 124


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Block until cursor-bridge run records exist, then report."
    )
    parser.add_argument("records", nargs="+", help="Absolute run-record JSON path(s)")
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between existence checks (default: 1)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Give up after SEC seconds (default: wait forever)",
    )
    return parser.parse_args(argv)


def _load_record(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    records = [Path(p) for p in args.records]
    deadline = (
        time.monotonic() + args.timeout if args.timeout is not None else None
    )

    results: dict[Path, dict] = {}
    while True:
        for path in records:
            if path in results:
                continue
            record = _load_record(path) if path.exists() else None
            if record is not None:
                results[path] = record
        if len(results) == len(records):
            break
        if deadline is not None and time.monotonic() >= deadline:
            missing = [str(p) for p in records if p not in results]
            print(
                "wait_cursor_run: timed out waiting for "
                + ", ".join(missing),
                file=sys.stderr,
            )
            for path in records:
                record = results.get(path)
                if record is not None:
                    print(f"{path}: {record.get('status')} (exit {record.get('exit_code')})")
                else:
                    print(f"{path}: <missing>")
            return EXIT_TIMEOUT
        time.sleep(max(args.interval, 0.05))

    first_failure = 0
    for path in records:
        record = results[path]
        status = record.get("status")
        exit_code = record.get("exit_code")
        print(f"{path}: {status} (exit {exit_code})")
        if first_failure == 0 and isinstance(exit_code, int) and exit_code != 0:
            first_failure = exit_code
        finished = record.get("finished_at") or "?"
        print(
            f"  finished={finished} head={record.get('head_before')}→"
            f"{record.get('head_after')} worker_status={record.get('worker_status')}",
            file=sys.stderr,
        )
    return first_failure


if __name__ == "__main__":
    raise SystemExit(main())
