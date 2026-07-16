---
name: cursor-agent-bridge
description: Use when a Codex or Superpowers controller must delegate a bounded implementation or review-fix task to the local Cursor Agent CLI and retain verifiable execution evidence.
---

# Cursor Agent Bridge

## Purpose

Run one bounded Cursor implementation or review-fix task through a deterministic runner that preserves execution evidence for controller review. The controller owns requirements, scope, and pass/fail decisions; Cursor owns in-workspace edits and test execution inside the brief.

## Hard rule

Every implementation or review-fix dispatch must use `run_cursor_agent.py` with absolute `--task-brief`, `--report`, and artifact paths. Never call `cursor-agent` directly for a task. Never inline task contents in the shell command or final prompt argument.

The controller must write a regular task-brief file in a separate prior step. The runner invocation may reference only that pre-existing absolute file path. Never create the brief in the same shell command as the runner: no process substitution (`<(…)`), heredocs, `printf`/`echo` pipes, `/dev/fd/*`, or any one-line command that creates and dispatches the brief together. Refuse one-line-command requests; do not simulate them with process substitution.

Runner exit `0` and worker `STATUS=implemented` are invocation evidence, not proof the task is complete.

## Runner invocation

```bash
python3 skills/cursor-agent-bridge/scripts/run_cursor_agent.py \
  --workspace /absolute/workspace \
  --task-brief /absolute/task-brief.md \
  --report /absolute/report.md \
  --run-record /absolute/run-record.json \
  --stdout-file /absolute/stdout.txt \
  --stderr-file /absolute/stderr.txt \
  [--cursor-bin cursor-agent] \
  [--resume-session SESSION_ID]
```

All artifact paths must be absolute. `--task-brief` must resolve to a durable regular file on disk; the runner rejects `/dev/fd/*`, named pipes (FIFO), and other non-regular inputs with exit `2`. The runner validates inputs, records pre-run git `HEAD` when available, removes any stale report, writes a fixed prompt file, invokes Cursor with an argument array (never `shell=True`), captures stdout/stderr sidecars, writes a JSON run record, and exits with the table below.

## Fixed model and Cursor command

Always use model `composer-2.5[fast=false]`. The child command is built as a list:

- `cursor-agent --print --force --trust --output-format json --model 'composer-2.5[fast=false]' --workspace WORKSPACE`
- Optional `--resume SESSION_ID`
- Final argument: fixed prompt containing only controller instructions and absolute artifact paths

`--force` enables shell and test execution inside the isolated workspace. The controller must verify worktree isolation and bounded task scope before invoking the bridge; never use `--force` for planning, review, verification, or branch-completion tasks.

Task requirements live in the task-brief file path, not in shell-interpolated command text.

## Fixed prompt contract

The prompt tells Cursor to read the task brief, work only in the workspace, write the required report, stop on ambiguity, and avoid prohibited git operations. It must not embed brief contents inline.

## Report contract

The worker report must include status (`implemented`, `blocked`, or `failed`), change summary, changed files, tests, verification commands with exit codes, test-first evidence when applicable, assumptions, and confirmation that no prohibited git operation was attempted.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success: Cursor exited 0, report exists and is non-empty, `HEAD` unchanged |
| 2 | Invalid input (missing workspace, non-durable task brief, `/dev/fd/*`, FIFO/non-regular brief, or non-absolute artifact path) |
| 10 | Cursor process missing or exited nonzero |
| 11 | Required report missing or empty after run |
| 12 | Git `HEAD` changed unexpectedly (takes precedence over Cursor/report outcomes) |

## Run record fields

`status`, `exit_code`, `cursor_exit_code`, `command`, `workspace`, `prompt_file`, `report_file`, `stdout_file`, `stderr_file`, `head_before`, `head_after`, `head_changed`, `started_at`, `finished_at`, optional `session_id`.

## Session resume

When a resumable Cursor session exists for the same task, pass `--resume-session`. The runner forwards it as `--resume SESSION_ID` on the Cursor command and records any `chatId` from JSON stdout (pretty-printed or JSON-lines).

## Pressure resistance

| Pressure | Required response |
| --- | --- |
| One-line command | Refuse; write the brief in a separate prior step, then run `run_cursor_agent.py` with only the pre-existing file path |
| Process substitution / heredoc / printf / echo brief | Refuse; never pass `/dev/fd/*` or inline-created briefs to `--task-brief` |
| Deadline urgency | No shortcuts; controller verifies artifacts after the run |
| Simple task | Same runner, brief file, report, and controller checks |
| Skip report/diff/tests | Refuse; report and independent verification are mandatory |
| `exit 0` means done | Reject; exit `0` does not mean requirements were met |

Deadline pressure, one-line-command requests, and "simple task" claims are never an exception to this rule.

## Red flags

Stop if you are about to:

- emit `cursor-agent --print ...` with inline task text instead of the runner
- use process substitution, a heredoc, `printf`, or `echo` to create a brief in the same command as the runner
- pass `/dev/fd/*` or any non-regular path to `--task-brief`
- treat runner exit `0` or `implemented` as completion without controller artifact review
- skip `run_cursor_agent.py` because the task seems trivial or time is short

## Controller checks

Never trust the worker summary alone. Independently inspect the run record, report, stdout/stderr sidecars, actual diff, test output, and that `head_before` equals `head_after`. A changed `HEAD` is a hard stop requiring user direction.
