# Execution Contracts

Reference for `executing-plans-with-cursor`. Read this file before the first dispatch.

## Artifact layout

All orchestration artifacts live under `.superpowers/cursor-execution/` inside the isolated workspace:

| Path | Purpose |
| --- | --- |
| `.superpowers/cursor-execution/progress.md` | Durable progress ledger — sole source of task state across interruptions |
| `.superpowers/cursor-execution/task-<id>/brief.md` | Bounded task brief for the active task |
| `.superpowers/cursor-execution/task-<id>/report.md` | Worker report path (written by Cursor) |
| `.superpowers/cursor-execution/task-<id>/review-brief.md` | Consolidated fix brief when review requires changes |
| `.superpowers/cursor-execution/task-<id>/controller-patch.md` | Durable mechanical controller-patch evidence |
| `.superpowers/cursor-execution/task-<id>/run-record.json` | Bridge run record |
| `.superpowers/cursor-execution/task-<id>/stdout.txt` | Captured stdout sidecar |
| `.superpowers/cursor-execution/task-<id>/stderr.txt` | Captured stderr sidecar |

Create the artifact root before the first dispatch.

## Task-brief schema

Write exactly one task brief at a time. Every brief must include:

- **Task identifier** and **purpose**
- **Exact requirements** and constraints copied from the approved plan
- **Allowed workspace** path and intended **file scope**
- **Test-first** behavior for feature or bug-fix tasks (expected failing result before implementation when applicable)
- **Acceptance criteria** and **verification command**(s) with expected outcomes
- **Prohibited git** and scope-changing actions (no commit, push, merge, rebase, reset, tag, or branch switch)
- **Report file path** and **report schema** (status, changes, tests, commands with exit codes, assumptions, git confirmation)
- Instruction to stop and report a **blocker** when requirements conflict or required context is unavailable

The controller writes the brief file before invoking the bridge. Cursor reads the brief path; the controller does not embed brief contents in shell commands.

## Progress ledger format

`progress.md` is the durable progress ledger. Each task entry records:

```markdown
## Task <id>: <title>
- Status: pending | in-review | fix-required | approved | blocked | failed
- Starting HEAD: <sha>
- Session ID: <id or none>
- Brief: .superpowers/cursor-execution/task-<id>/brief.md
- Report: .superpowers/cursor-execution/task-<id>/report.md
- Last review: <timestamp> — <approved|fix-required|blocked>
- Notes: <blockers, concerns, minor findings deferred to final review>
```

Update the ledger after every review decision. Do not mark a task `approved` until `reviewing-cursor-changes` passes. The ledger, not the worker summary, defines what is done.

## Mechanical controller-patch contract

When `reviewing-cursor-changes` identifies a finding that qualifies for the mechanical review-patch exception, the controller may patch directly instead of routing to Cursor. The exception is semantics-based: **minor** severity or a small line count alone is **not** sufficient.

**Allowlist (exhaustive):** formatter output; whitespace; a typo in non-executable prose or a comment.

**Denylist (never patch):** executable code and tests; configuration and schemas; dependencies, lockfiles, and generated output; public APIs; security, authentication, data, and business logic; commands and code blocks in documentation.

Requirements:

- Patch only files in the active brief's **allowed files** with unambiguous ownership and **no scope expansion**.
- Keep the task **`in-review`** while applying the patch.
- Write `.superpowers/cursor-execution/task-<id>/controller-patch.md` with the **finding**, **classification**, changed files/diff, **controller identity**, and **verification** results.
- Rerun the **exact covering verification** commands from the brief.
- **Re-review** the fresh diff before changing status to `approved`.

If classification is uncertain, the patch grows, scope expands, or verification fails, stop and route **one consolidated fix brief** through `cursor-agent-bridge` instead.

## Blocker handling

Stop the sequential loop and record the blocker in `progress.md` when:

| Condition | Action |
| --- | --- |
| Cursor CLI or requested model unavailable | Stop; record blocker |
| Bridge returns unexpected `HEAD` change | Stop; record blocker |
| Required report missing or empty despite exit `0` | Stop; record blocker |
| Review returns `blocked` or requirements conflict | Stop; record blocker |
| Out-of-scope changes cannot be resolved safely | Stop; record blocker |
| Git state does not match ledger after interruption | Stop; record blocker |

Do not reset history, auto-commit, or patch semantic implementation code as the controller. Mechanical review patches are the sole exception and must follow the contract above. Report the blocker and wait for user direction.
