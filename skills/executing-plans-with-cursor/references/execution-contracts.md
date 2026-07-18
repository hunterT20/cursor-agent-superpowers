# Execution Contracts

Reference for `executing-plans-with-cursor`. Read this file before the first dispatch.

## Artifact layout

### Integration worktree (authoritative)

All orchestration state lives in the **integration worktree** under `.superpowers/cursor-execution/`:

| Path | Purpose |
| --- | --- |
| `.superpowers/cursor-execution/progress.md` | **Authoritative integration ledger** — sole source of task and wave state across interruptions |
| `.superpowers/cursor-execution/wave-<id>/evidence.md` | Wave dependency graph, disjoint write-set declaration, and wave-base integration HEAD |
| `.superpowers/cursor-execution/task-<id>/brief.md` | Bounded task brief for sequential dispatch or controller-written dispatch brief |
| `.superpowers/cursor-execution/task-<id>/review-brief.md` | Consolidated fix brief when review requires changes |
| `.superpowers/cursor-execution/task-<id>/controller-patch.md` | Durable mechanical controller-patch evidence |

Create the integration artifact root before the first dispatch.

### Task worktree (task-scoped execution artifacts)

Each parallel-wave task worktree holds **task-scoped execution artifacts/evidence** — controller-written and worker-written files for that task:

| Path | Purpose |
| --- | --- |
| `.superpowers/cursor-execution/task-<id>/brief.md` | Bounded task brief (controller-written before dispatch) |
| `.superpowers/cursor-execution/task-<id>/review-brief.md` | Consolidated fix brief when review requires changes (controller-written) |
| `.superpowers/cursor-execution/task-<id>/controller-patch.md` | Durable mechanical controller-patch evidence (controller-written) |
| `.superpowers/cursor-execution/task-<id>/report.md` | Worker report (written by Cursor) |
| `.superpowers/cursor-execution/task-<id>/run-record.json` | Bridge run record |
| `.superpowers/cursor-execution/task-<id>/stdout.txt` | Captured stdout sidecar |
| `.superpowers/cursor-execution/task-<id>/stderr.txt` | Captured stderr sidecar |

Task-scoped execution artifacts are **evidence**, not alternate state authorities. Only the **integration ledger** and wave evidence in the **integration worktree** define state.

## Worktree boundaries

- The initial isolated workspace is the **integration worktree**.
- Parallel-wave **task worktrees** are **sibling isolated worktrees**, **never nested** inside another linked worktree.
- Create sibling task worktrees through the platform-native worktree mechanism when available; otherwise apply `superpowers:using-git-worktrees` safety rules from the repository's **primary/common checkout**, not by recursively invoking it inside a linked worktree.
- Record every task's **absolute worktree path** in the authoritative integration ledger.

## Routing gates

**Sequential execution is the safe default** in the integration worktree. A simple sequential plan requires task boundaries, allowed files, and acceptance evidence — **not** a dependency graph or write-set declaration.

Authorize a **parallel isolated wave** only when every gate below passes:

1. **Dependency graph** — explicit graph with **no direct or transitive dependency edge** among wave tasks.
2. **Disjoint write sets** — declared **intended write sets** are **disjoint**.
3. **No shared integration-sensitive contracts** — tasks share no **API**, **schema**, **configuration** surface, dependency/**lockfile**, **generated output**, **migration** chain, or other integration-sensitive mutable contract.

**File disjointness alone is insufficient.** An `independent` label alone is insufficient. When parallel proof is **missing, incomplete, or ambiguous**, route **sequentially**.

Concurrency is capped at **three** concurrently active Cursor tasks per wave.

## Parallel wave isolation

Every task in a parallel wave receives its own:

- **branch** and **sibling isolated git worktree**;
- **one fresh Cursor session**;
- task-scoped **execution artifact root** (brief, review-brief, controller-patch, report, run record, stdout, stderr);
- `reviewing-cursor-changes` review gate; and
- **bridge `HEAD` invariant** across every Cursor invocation.

All task branches in one wave start from the same recorded **wave-base integration HEAD**. **Later waves** branch from the **updated integration HEAD** recorded after the prior wave completes.

Cursor must **not** commit, push, merge, rebase, reset, tag, switch branches, or create/remove worktrees. The controller owns task commits and integration.

## Bridge HEAD invariant and controller commits

- The **bridge `HEAD` invariant** applies across **every Cursor invocation**. Any unexpected worker `HEAD` mutation stops the active task or wave.
- After a task reaches **`approved-isolated`**, the controller may create **exactly the recorded task commit** on that task branch and must store the **task commit SHA** in the integration ledger before integration begins.
- After each sequential integration into the integration branch, record the **integrated HEAD** in the integration ledger.
- **Unrecorded HEAD changes remain blockers.**

## Task-brief schema

Write exactly one task brief at a time per active dispatch. Every brief must include:

- **Task identifier** and **purpose**
- **Exact requirements** and constraints copied from the approved plan
- **Allowed workspace** path and intended **file scope**
- **Test-first** behavior for feature or bug-fix tasks (expected failing result before implementation when applicable)
- **Acceptance criteria** and **verification command**(s) with expected outcomes
- **Prohibited git** and scope-changing actions (no commit, push, merge, rebase, reset, tag, branch switch, or worktree operations)
- **Report file path** and **report schema** (status, changes, tests, commands with exit codes, assumptions, git confirmation)
- Instruction to stop and report a **blocker** when requirements conflict or required context is unavailable

The controller writes the brief file before invoking the bridge. Cursor reads the brief path; the controller does not embed brief contents in shell commands.

## Progress ledger format

`.superpowers/cursor-execution/progress.md` in the **integration worktree** is the **authoritative integration ledger** — the sole source of task and wave state. After interruption, **resume from the integration ledger**, then verify every recorded branch, **absolute worktree path**, artifact root, and git state.

Each task entry records:

```markdown
## Task <id>: <title>
- Status: pending | in-review | fix-required | approved-isolated | approved | blocked | failed
- Branch: <branch name>
- Worktree path: <absolute path or integration worktree for sequential>
- Artifact root: <absolute path>
- Wave-base HEAD: <sha or n/a>
- Session ID: <id or none>
- Review state: <last verdict and timestamp>
- Task commit SHA: <sha or none>
- Integrated HEAD: <sha or none>
- Brief: <absolute brief path>
- Report: <absolute report path>
- Notes: <blockers, concerns, minor findings deferred to final review>
```

Update the integration ledger after every review decision and after every controller commit or integration step.

In sequential mode, do not mark a task `approved` until `reviewing-cursor-changes` passes.

In parallel mode, mark `approved-isolated` after isolated review passes. **Integration may start only when every wave task is `approved-isolated`.** Do **not** integrate a subset when any task is `blocked`, `failed`, unresolved, or missing required artifacts. Mark `approved` only after the controller commits each task branch (recording **task commit SHA**), integrates sequentially in plan order (recording **integrated HEAD** after each step), reruns **affected verification after every integration**, and reruns the **full required suite at wave end**.

## Integration gate

After **all** wave tasks reach `approved-isolated`:

1. The **controller commits** each `approved-isolated` task branch and records the **task commit SHA**.
2. **Integrate branches one at a time** into the integration branch in **declared plan order**, recording the **integrated HEAD** after each integration.
3. Rerun **affected verification after every integration**.
4. Rerun the **full required suite at wave end**.
5. Only then mark tasks **`approved`**.

**Pre-integration rule:** do **not** integrate a subset when any task is `blocked`, `failed`, unresolved, or missing required artifacts. Every wave task must be `approved-isolated` before integration begins.

**Mid-integration failure:** if a merge conflict or affected/full verification fails after one or more branches are already integrated:

- **preserve and record every already-integrated HEAD**;
- **stop before integrating any remaining branch**;
- **do not reset, rewrite, or auto-rollback history**;
- mark the wave **`blocked`** and require an **explicit recovery decision** (for example a fresh recovery branch/worktree from the recorded **pre-wave HEAD**).

Any `blocked`, `failed`, unresolved, overlap, unexpected worker `HEAD` mutation, merge conflict, or integration-test failure **stops the wave** and **prevents integration of every not-yet-integrated branch**.

Conversation memory and worker summaries are never sources of truth for wave state.

## Mechanical controller-patch contract

When `reviewing-cursor-changes` identifies a finding that qualifies for the mechanical review-patch exception, the controller may patch directly instead of routing to Cursor. The exception is semantics-based: **minor** severity or a small line count alone is **not** sufficient.

**Allowlist (exhaustive):** formatter output; whitespace; a typo in non-executable prose or a comment.

**Denylist (never patch):** executable code and tests; configuration and schemas; dependencies, lockfiles, and generated output; public APIs; security, authentication, data, and business logic; commands and code blocks in documentation.

Requirements:

- Patch only files in the active brief's **allowed files** with unambiguous ownership and **no scope expansion**.
- Keep the task **`in-review`** while applying the patch.
- Write `.superpowers/cursor-execution/task-<id>/controller-patch.md` with the **finding**, **classification**, changed files/diff, **controller identity**, and **verification** results.
- Rerun the **exact covering verification** commands from the brief.
- **Re-review** the fresh diff before changing status to `approved-isolated` or `approved`.

If classification is uncertain, the patch grows, scope expands, or verification fails, stop and route **one consolidated fix brief** through `cursor-agent-bridge` instead.

## Blocker handling

Stop the active loop and record the blocker in the **integration ledger** when:

| Condition | Action |
| --- | --- |
| Cursor CLI or requested model unavailable | Stop; record blocker |
| Bridge returns unexpected `HEAD` change or worker `HEAD` mutation | Stop; record blocker |
| Unrecorded `HEAD` change on integration or task branch | Stop; record blocker |
| Required report or artifact missing or empty despite exit `0` | Stop; record blocker |
| Review returns `blocked` or requirements conflict | Stop; record blocker |
| Out-of-scope changes cannot be resolved safely | Stop; record blocker |
| Git state does not match integration ledger after interruption | Stop; record blocker |
| Parallel wave: overlapping write or integration surface | Stop the wave; record blocker; do not integrate not-yet-integrated branches |
| Parallel wave: any task `blocked`, `failed`, or unresolved | Stop the wave; prevent integration of not-yet-integrated branches |
| Parallel wave: **merge conflict** | Stop the wave; **do not automatically merge** remaining branches |
| Parallel wave: **integration-test failure** during sequential integration | Stop the wave; preserve already-integrated HEADs; do not auto-rollback; require explicit recovery decision |

Do not reset history, auto-commit, or patch semantic implementation code as the controller. Mechanical review patches are the sole exception and must follow the contract above. Report the blocker and wait for user direction.
