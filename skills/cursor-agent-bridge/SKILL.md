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

Invoke the runner by its absolute path inside this skill's directory (`scripts/run_cursor_agent.py`). Do not rely on a repo-relative `skills/` path — after installation the skill directory lives wherever the host placed it.

```bash
python3 /absolute/path/to/cursor-agent-bridge/scripts/run_cursor_agent.py \
  --workspace /absolute/workspace \
  --task-brief /absolute/task-brief.md \
  --report /absolute/report.md \
  --run-record /absolute/run-record.json \
  --stdout-file /absolute/stdout.txt \
  --stderr-file /absolute/stderr.txt \
  [--cursor-bin cursor-agent] \
  [--resume-session SESSION_ID] \
  [--timeout SECONDS] \
  [--expect-clean] \
  [--allowed-file PATH ...] \
  [--notify-command CMD]
```

All artifact paths must be absolute and distinct after resolution. `--task-brief` must resolve to a durable, non-empty, readable regular file on disk; the runner rejects `/dev/fd/*`, named pipes (FIFO), empty briefs, colliding artifact paths, and non-regular output paths (existing directories, FIFOs, sockets, devices) with exit `2`. The runner validates inputs, takes an exclusive per-workspace dispatch lock (exit `17` when held), records pre-run git `HEAD`, index signature, repo root, and uncommitted-change set when available, removes any stale report, writes a fixed prompt file, invokes Cursor with an argument array (never `shell=True`) using the workspace as the child process working directory in its own process group (a timeout kills the whole tree, not just the CLI), captures stdout/stderr sidecars, writes a JSON run record, and exits with the table below.

`--allowed-file` copies the brief's allowed file scope into the command as a **repeated flag** (workspace-relative paths; a trailing `/` allows a whole directory). After the run, worker file changes outside the list fail with exit `14`. `.superpowers/` execution artifacts and the runner's own artifact paths are always excluded. When the plan defines file scope, always pass it — scope becomes a code-level gate, not only a review judgment.

`--expect-clean` refuses dispatch (exit `18`) unless the workspace has no uncommitted changes outside `.superpowers/` and artifact paths. Use it for every sequential dispatch after the first task commit baseline exists.

## Fixed model and Cursor command

Always use model `composer-2.5[fast=false]`. The child command is built as a list and launched with the selected workspace as its process working directory. Cursor discovers project `.cursor/cli.json` from process cwd, so the controller's cwd must never leak an unrelated repository config into the worker:

- `cursor-agent --print --force --trust --output-format json --model 'composer-2.5[fast=false]' --workspace WORKSPACE`
- Optional `--resume SESSION_ID`
- Final argument: fixed prompt containing only controller instructions and absolute artifact paths

`--force` enables shell and test execution inside the isolated workspace. The controller must verify worktree isolation and bounded task scope before invoking the bridge; never use `--force` for planning, review, verification, or branch-completion tasks.

Task requirements live in the task-brief file path, not in shell-interpolated command text.

## Fixed prompt contract

The prompt tells Cursor to read the task brief, work only in the workspace, write the required report, stop on ambiguity, and avoid prohibited git operations. It must not embed brief contents inline.

## Report contract

The worker report must include a `Status:` line whose value is exactly `implemented`, `blocked`, or `failed` — the runner parses it into `worker_status` and maps `blocked`/`failed` to dedicated exit codes. The report also includes change summary, changed files, tests, verification commands with exit codes, test-first evidence when applicable, assumptions, and confirmation that no prohibited git operation was attempted.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success: Cursor exited 0, report exists and is non-empty, `HEAD` and index unchanged |
| 2 | Invalid input (missing workspace, non-durable/empty task brief, `/dev/fd/*`, FIFO/non-regular brief, or non-absolute, colliding, or non-regular artifact path) |
| 10 | Cursor process missing or exited nonzero |
| 11 | Required report missing or empty after run |
| 12 | Git `HEAD` or index changed unexpectedly (takes precedence over Cursor/report outcomes) |
| 13 | Cursor run exceeded `--timeout`; the whole process group was killed |
| 14 | Worker file changes violated `--allowed-file` scope (`scope_violation`) |
| 15 | Worker report declared `Status: blocked` (`worker_blocked`) |
| 16 | Worker report declared `Status: failed` (`worker_failed`) |
| 17 | Another dispatch already holds this workspace's lock (`dispatch_locked`) |
| 18 | `--expect-clean` given but workspace has uncommitted changes (`dirty_workspace`) |

## Run record fields

`status`, `exit_code`, `cursor_exit_code`, `command`, `workspace`, `controller_cwd`, `cursor_cwd`, `repo_root`, `cursor_version`, `test_hook`, `timed_out`, `task_brief`, `prompt_file`, `report_file`, `stdout_file`, `stderr_file`, `lock_file`, `head_before`, `head_after`, `head_changed`, `index_changed`, `changed_files`, `scope_check`, `scope_violated_files`, `worker_status`, `notify_command`, `started_at`, `finished_at`, optional `session_id`.

`changed_files` records worker-attributable uncommitted paths (changes present before dispatch are excluded). `scope_check` is `passed`, `failed`, `skipped_non_git`, or `not_configured`. `worker_status` mirrors the report's `Status:` token.

The git-state invariant covers both `HEAD` and the index: `git add`, `git stash`, `git reset`, and similar staging mutations are violations even when `HEAD` does not move. `repo_root` records `git rev-parse --show-toplevel` before dispatch; `cursor_version` records the worker binary version for evidence.

## Completion signaling — do not poll

The run record is written **once, atomically**, only when the run ends. Its existence is the completion signal; intermediate files (prompt, sidecars) may appear earlier and mean nothing.

- **Blocking wait (preferred):** `scripts/wait_cursor_run.py RECORD.json [RECORD2.json ...] [--timeout SEC]` sleeps inside the process until every record exists, then prints each `status`/`exit_code` and exits with the first nonzero record code. One invocation = one blocked tool call; the process waits, the controller does not poll. Pass several run records to wait on a whole parallel wave at once.
- **Run synchronously:** invoking `run_cursor_agent.py` and simply waiting for it to return is equivalent — the call ends when Cursor exits.
- **Push notification (optional):** `--notify-command CMD` runs the controller-provided command once after the record is written, with `CURSOR_RUN_RECORD`, `CURSOR_EXIT_CODE`, `CURSOR_STATUS`, `CURSOR_WORKSPACE` in its environment — e.g. `osascript -e 'display notification "cursor task done"'` or a webhook `curl`. Failures never change the exit code. Never let the worker or brief define this command; it is controller-side only.

Never poll run state in a loop from the controller — wait on the record file or the process.

## Session resume

When a resumable Cursor session exists for the same task, pass `--resume-session`. The runner forwards it as `--resume SESSION_ID` on the Cursor command and records the first nonempty session identifier from JSON stdout (pretty-printed or JSON-lines), checking keys in order: `session_id`, `sessionId`, `chatId`.

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
- reuse one path for two artifacts or pass an empty brief, a directory, or another non-regular path as an output artifact
- omit `--allowed-file` when the brief defines a file scope, or run two dispatches against the same workspace concurrently
- treat runner exit `0` or `implemented` as completion without controller artifact review
- skip `run_cursor_agent.py` because the task seems trivial or time is short

## Controller checks

Never trust the worker summary alone. Independently inspect the run record, report, stdout/stderr sidecars, actual diff, test output, and that `head_before` equals `head_after` with `index_changed` false. Check `scope_check`/`scope_violated_files` and `worker_status` — `blocked`/`failed` reports and scope violations fail the run even when the worker exited `0`. A changed `HEAD` or index is a hard stop requiring user direction.
