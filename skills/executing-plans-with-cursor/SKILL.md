---
name: executing-plans-with-cursor
description: Use when an approved implementation plan must be executed task-by-task by Cursor Agent, defaulting to sequential dispatch in one worktree and allowing parallel isolated waves only when dependency and integration-surface proof is explicit.
---

# Executing Plans with Cursor

## Prerequisites

Do not dispatch any task until all of the following are true:

1. **Approved implementation plan** — explicit task boundaries, allowed files, and acceptance evidence. Do not improvise scope.
2. **Integration worktree** — follow `superpowers:using-git-worktrees` and confirm one **isolated worktree** serving as the integration worktree before first dispatch. Record the integration branch and initial `HEAD`.
3. **Required sub-skills loaded** — read `cursor-agent-bridge` for dispatch mechanics and `reviewing-cursor-changes` for the review gate. Reference them; do not copy procedures.
4. **Execution contracts read** — read `references/execution-contracts.md` before first dispatch for artifact paths, task-brief schema, authoritative integration ledger format, routing gates, and blocker matrix.

Codex and the controller must not edit implementation code during execution. Every implementation edit and every semantic review-fix edit belongs to Cursor Agent. A **mechanical review patch** is the sole controller exception and must follow `reviewing-cursor-changes` plus `references/execution-contracts.md`.

## Routing decision

**Sequential execution is the safe default.** Use the integration worktree and the sequential dispatch loop below unless every gate in `references/execution-contracts.md` proves a dependency-free parallel wave.

Route to a **parallel isolated wave** only when the controller authorizes it and the approved plan includes:

- an explicit **dependency graph** with **no direct or transitive dependency edge** among the wave tasks;
- declared **intended write sets** that are **disjoint**; and
- proof that tasks share **no API, schema, configuration surface, dependency/lockfile, generated output, migration chain, or other integration-sensitive mutable contract**.

**File disjointness alone is insufficient.** An `independent` label alone is insufficient. When parallel proof is **missing, incomplete, or ambiguous**, execute **sequentially** — a simple sequential plan does **not** need a dependency graph or write-set declaration.

Cap each parallel wave at **three** concurrently active Cursor tasks. Never fan-out parallel implementers in one worktree.

## Sequential dispatch loop

Execute the approved plan **sequentially** in the **integration worktree** when the routing decision does not authorize a parallel wave.

For each task in plan order:

1. Read the authoritative integration ledger at `.superpowers/cursor-execution/progress.md` and verify git `HEAD` matches the ledger's recorded state.
2. If the task is not already complete, write `task-<id>/brief.md` under the integration worktree artifact root per `references/execution-contracts.md`.
3. Start **one fresh Cursor session per task** through `cursor-agent-bridge` (`run_cursor_agent.py`). Never call `cursor-agent` directly. The **bridge `HEAD` invariant** applies across **every Cursor invocation** — any unexpected worker `HEAD` mutation is a blocker.
4. Wait for the bridge run to finish. Bridge exit `0` and worker `STATUS=implemented` are invocation evidence, **not** task completion.
5. Load `reviewing-cursor-changes` and review run record, report, diff, test output, and `HEAD` invariants. Apply a mechanical review patch only when the review skill and execution-contract reference authorize it; route all semantic fixes through the bridge.
6. If review verdict is `fix-required`, write one consolidated `review-brief.md` and re-dispatch through the bridge. **Resume only within this task's review-fix loop** using `--resume-session` when resumable; otherwise start fresh with both brief paths.
7. Mark the task `approved` in the integration ledger only after `reviewing-cursor-changes` returns `approved` with sufficient evidence.
8. Proceed to the next task — no skip review, no advance on a worker success message alone.

Repeat until every plan task has a ledger entry marked `approved` or the workflow is blocked. After interruption, **resume from the authoritative integration ledger**, verify every recorded branch/worktree/artifact path and git state, then continue — not from conversation memory. Worker reports and local artifacts are **evidence**, not alternate state authorities.

## Parallel isolated wave loop

When the routing decision authorizes a parallel wave:

1. Record the wave identifier, dependency graph, write-set declaration, and **wave-base integration HEAD** in wave evidence under the **integration worktree** (see `references/execution-contracts.md`).
2. For each task in the wave (up to three concurrently active Cursor tasks), the controller creates from the repository's **primary/common checkout** (or platform-native worktree mechanism when available):
   - its own **branch** and **sibling isolated git worktree** — **never nested** inside another linked worktree;
   - starting from the same recorded **wave-base integration HEAD**;
   - task-scoped **execution artifacts/evidence** (`brief.md`, `review-brief.md`, `controller-patch.md`, `report.md`, `run-record.json`, `stdout.txt`, `stderr.txt`) inside that task worktree;
   - **one fresh Cursor session per task** through `cursor-agent-bridge`. Never call `cursor-agent` directly.
   Do **not** recursively invoke `superpowers:using-git-worktrees` from inside a linked worktree. Record every task's **absolute worktree path**, branch, artifact root, wave-base HEAD, and session in the **authoritative integration ledger**.
3. Cursor must **not** commit, push, merge, rebase, reset, tag, switch branches, or create/remove worktrees. The controller owns task commits and integration.
4. For each task, run `reviewing-cursor-changes` on run record, report, diff, test output, and **bridge `HEAD` invariants**. Apply mechanical review patches only per `reviewing-cursor-changes` and `references/execution-contracts.md`.
5. A task that passes isolated review becomes **`approved-isolated`**, not `approved` or complete. Re-dispatch through the bridge for `fix-required` verdicts; **resume only within that task's review-fix loop**.
6. **Integration may start only when every wave task is `approved-isolated`.** `fix-required` remains inside that task's review loop. Any `blocked`, `failed`, unresolved, overlap, unexpected worker **`HEAD` mutation**, or missing artifact **stops the wave** and **prevents integration of every not-yet-integrated branch**. **Do not integrate a subset** because other tasks passed.
7. After **all** wave tasks are `approved-isolated`:
   - the **controller commits** each approved task branch and records the **task commit SHA** in the integration ledger before integration;
   - **integrates branches one at a time** into the integration branch in **declared plan order**;
   - records the **integrated HEAD** after each sequential integration;
   - reruns **affected verification after every integration**;
   - reruns the **full required suite at wave end**;
   - only then marks tasks **`approved`** in the integration ledger.
   If a **merge conflict** or **affected/full verification failure** occurs during sequential integration after one or more branches are already integrated:
   - **preserve and record every already-integrated HEAD**;
   - **stop before integrating any remaining branch**;
   - **do not reset, rewrite, or auto-rollback history**;
   - mark the wave **`blocked`** and require an **explicit recovery decision** (for example a fresh recovery branch/worktree from the recorded **pre-wave HEAD**).
8. **Later waves** branch from the **updated integration HEAD** recorded after the prior wave completes.

**Unrecorded HEAD changes remain blockers.** Stop the wave and record the blocker when any of the following occur before integration completes: overlapping write or **integration surface**, unexpected worker **`HEAD` mutation**, **merge conflict**, or **integration-test failure**. **Do not automatically merge** remaining not-yet-integrated branches. Fall back to a **fresh sequential path** or an explicit recovery decision — never imply history can be rolled back automatically.

## Session rules

- **One fresh Cursor session per task** for the initial implementation dispatch.
- Reuse the same task's session **only** for review-fix iterations on that task.
- Never reuse a session across different tasks.
- Never start a second implementation session for the same task while a prior attempt is unresolved.
- When resume is unavailable, start fresh with task and review brief paths.

## Pressure resistance

| Pressure | Required response |
| --- | --- |
| Fan-out parallel workers / "run all three at once" without proof | Refuse; route sequentially unless dependency graph, disjoint write sets, and integration-surface proof are explicit |
| Independent tasks can run in parallel | Refuse without proof; an `independent` label alone is insufficient |
| File disjointness proves safety | Refuse; file disjointness alone is insufficient |
| Integrate passing tasks while one is blocked | Refuse; do not integrate a subset — every wave task must be `approved-isolated` first |
| Worker success message means done | Reject; verify artifacts and run `reviewing-cursor-changes` |
| Bridge exit `0` means done | Reject; exit `0` is not task completion |
| Skip review to save time | Refuse; review before ledger completion and before integration |
| Controller implements because it is faster | Refuse; controller must not edit implementation or semantic review-fix code |
| Controller patches outside mechanical allowlist | Refuse; route consolidated fix brief through the bridge per `reviewing-cursor-changes` |
| Pressure to bypass proof gates | Refuse; proof gates are not bypassed by deadlines or speed pressure |

Parallel dispatch **without dependency and integration proof**, partial wave integration, worker success messages, and skipped review are **never an exception**.

## Red flags

Stop if you are about to:

- fan-out or dispatch parallel Cursor implementers in one worktree
- require a dependency graph or write-set declaration for a purely sequential plan
- authorize a parallel wave without an explicit dependency graph, disjoint write sets, and integration-surface proof
- treat file disjointness or an `independent` label as sufficient for parallel execution
- integrate a subset while another wave task is blocked or failed, or start integration before every wave task reaches `approved-isolated`
- treat worker reports or task-worktree local artifacts as alternate state authorities
- mark a parallel-wave task `approved` before isolated review, controller commits, sequential integration, and verification complete
- treat a worker success message or bridge exit `0` as task completion without review
- call `cursor-agent` directly instead of `cursor-agent-bridge` / `run_cursor_agent.py`
- resume from conversation memory without reading the authoritative integration ledger and verifying every recorded path and git state
- edit implementation or semantic review-fix code as the controller (mechanical review patches are the sole exception per `reviewing-cursor-changes` and `references/execution-contracts.md`)
- advance integration while review is pending, `fix-required`, or a wave blocker is unresolved
- let Cursor commit, push, merge, rebase, reset, tag, switch branches, or manage worktrees
- create nested task worktrees or omit task worktree paths from the integration ledger
