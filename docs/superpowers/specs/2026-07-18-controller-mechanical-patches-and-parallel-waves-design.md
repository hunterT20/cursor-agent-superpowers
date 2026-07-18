# Controller Mechanical Patches and Parallel Waves Design

Date: 2026-07-18
Status: Approved

## Goal

Reduce avoidable Cursor round trips without weakening semantic review or task isolation:

1. allow the controller to apply a narrowly defined mechanical review patch and verify it again; and
2. allow proven-independent plan tasks to run concurrently in separate isolated worktrees, followed by sequential integration.

## Controller mechanical patch exception

The exception is based on edit semantics, not finding severity. A finding labeled `minor` is not automatically controller-editable.

The controller may patch a review finding only when every condition below holds:

- the edit is deterministic and non-semantic;
- it is limited to formatter output, whitespace, or a typo in non-executable prose or a comment;
- the file is already allowed by the active task brief;
- ownership is unambiguous and the patch does not expand scope;
- the controller records the patch and reruns the exact covering verification commands before approval.

The exception never applies to executable code, tests, configuration, schemas, dependencies, lockfiles, generated output, public APIs, security/auth/data/business logic, or commands and code blocks in documentation.

If classification is uncertain, the patch grows beyond the mechanical finding, or verification fails, the controller must stop and route one consolidated fix brief back to Cursor through the existing bridge. The task remains `in-review` until fresh evidence passes and the controller re-reviews the resulting diff.

## Parallel isolated worktree waves

Sequential execution remains the default. Parallel execution is an explicit optimization for a dependency-free wave.

Before dispatch, the controller must produce a dependency graph and write-set declaration. Two tasks may share a parallel wave only when:

- no direct or transitive dependency edge exists between them;
- their intended write sets are disjoint; and
- they do not share an API, schema, configuration surface, lockfile, generated output, migration chain, or other integration-sensitive contract.

File disjointness alone is insufficient. When proof is missing or ambiguous, tasks execute sequentially.

Each task in a parallel wave receives its own branch, isolated worktree, fresh Cursor session, artifact directory, progress entry, report, run record, review gate, and `HEAD` invariant. Concurrency is capped at three tasks.

An isolated task can reach `approved-isolated`, not final completion. The controller then commits approved task branches and integrates them one at a time into the integration branch in dependency-plan order. It runs affected verification after every integration and the full required suite after the wave. Later waves branch from the updated integration `HEAD`.

Any worktree overlap, unexpected `HEAD` change, merge conflict, or integration-test failure stops the wave. No remaining branch is merged automatically; unresolved work falls back to a fresh sequential path.

## Artifact model

The normal shared-worktree ledger remains valid for sequential plans. A parallel run adds:

- a wave identifier and explicit dependency/write-set evidence;
- one task-scoped artifact root per isolated worktree;
- an `approved-isolated` state;
- integration commit and verification evidence in the integration ledger.

Conversation memory and worker summaries are never sources of truth for wave state.

## Scope

Update the overlay entry skill, execution skill, review skill, execution-contract reference, README, and contract tests. Do not change the bridge runner, fixed Cursor model, prohibited worker git operations, or controller ownership of integration commits.

## Acceptance

- Contract tests prove the mechanical allowlist, semantic denylist, required patch evidence, exact re-verification, and Cursor fallback.
- Contract tests prove sequential-by-default behavior, explicit dependency/write-set gates, isolated worktrees, concurrency cap, `approved-isolated`, sequential integration, per-integration and full-wave verification, and stop/fallback rules.
- Existing routing, bridge, review, `HEAD`, scope, and evidence gates remain green.
- All changed skills pass the skill validator and `git diff --check`.
