---
name: executing-plans-with-cursor
description: Use when an approved implementation plan must be executed task-by-task by Cursor Agent inside one isolated project workspace.
---

# Executing Plans with Cursor

## Prerequisites

Do not dispatch any task until all of the following are true:

1. **Approved implementation plan** — explicit task boundaries, allowed files, and acceptance evidence. Do not improvise scope.
2. **Isolated worktree** — follow `superpowers:using-git-worktrees` and confirm isolated workspace before first dispatch. Record initial branch and `HEAD`.
3. **Required sub-skills loaded** — read `cursor-agent-bridge` for dispatch mechanics and `reviewing-cursor-changes` for the review gate. Reference them; do not copy procedures.
4. **Execution contracts read** — read `references/execution-contracts.md` before first dispatch for artifact paths, task-brief schema, progress ledger format, and blocker matrix.

Codex and the controller must not edit implementation code during execution; every implementation and review-fix edit belongs to Cursor Agent.

## Sequential dispatch loop

Execute the approved plan **sequentially** in one **shared worktree**. Never dispatch parallel Cursor implementers, never fan-out, and never run multiple implementation tasks at once — **even when** plan tasks are labeled independent.

For each task in plan order:

1. Read `progress.md` and verify git `HEAD` matches the ledger's recorded state.
2. If the task is not already complete, write `task-<id>/brief.md` per `references/execution-contracts.md`.
3. Start **one fresh Cursor session per task** through `cursor-agent-bridge` (`run_cursor_agent.py`). Never call `cursor-agent` directly.
4. Wait for the bridge run to finish. Bridge exit `0` and worker `STATUS=implemented` are invocation evidence, **not** task completion.
5. Load `reviewing-cursor-changes` and review run record, report, diff, test output, and `HEAD` invariants.
6. If review verdict is `fix-required`, write one consolidated `review-brief.md` and re-dispatch through the bridge. **Resume only within this task's review-fix loop** using `--resume-session` when resumable; otherwise start fresh with both brief paths.
7. Mark the task complete in `progress.md` only after `reviewing-cursor-changes` returns `approved` with sufficient evidence.
8. Proceed to the next task — no skip review, no advance on a worker success message alone.

Repeat until every plan task has a ledger entry marked complete or the workflow is blocked. After interruption, resume from `progress.md` and verified git state — not from conversation memory.

## Session rules

- **One fresh Cursor session per task** for the initial implementation dispatch.
- Reuse the same task's session **only** for review-fix iterations on that task.
- Never reuse a session across different tasks.
- Never start a second implementation session for the same task while a prior attempt is unresolved.
- When resume is unavailable, start fresh with task and review brief paths.

## Pressure resistance

| Pressure | Required response |
| --- | --- |
| Fan-out parallel workers / "run all three at once" | Refuse; tasks stay sequential in one shared worktree |
| Independent tasks can run in parallel | Refuse; independent labels never justify parallel implementers |
| Worker success message means done | Reject; verify artifacts and run `reviewing-cursor-changes` |
| Bridge exit `0` means done | Reject; exit `0` is not task completion |
| Skip review to save time | Refuse; review before ledger completion and before the next task |
| Controller implements because it is faster | Refuse; controller must not edit implementation |

Parallel dispatch, worker success messages, and skipped review are **never an exception** — not for deadlines, simple tasks, or independent plan tasks.

## Red flags

Stop if you are about to:

- fan-out or dispatch parallel Cursor implementers in one worktree
- treat a worker success message or bridge exit `0` as task completion without review
- mark `progress.md` complete before `reviewing-cursor-changes` approves
- call `cursor-agent` directly instead of `cursor-agent-bridge` / `run_cursor_agent.py`
- resume from conversation memory without reading `progress.md` and verifying git state
- edit implementation code as the controller
- advance to the next task while review is pending or fix-required
