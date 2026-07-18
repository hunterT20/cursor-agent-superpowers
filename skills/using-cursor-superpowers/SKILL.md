---
name: using-cursor-superpowers
description: Use when a user wants a controller to plan, review, or verify work while Cursor Agent performs every semantic implementation and semantic review-fix edit and the controller may apply only verified mechanical review patches. Upstream Superpowers is optional; when available, ask once per task before routing through upstream workflows.
---

# Using Cursor Superpowers

## Core role boundary

The Codex or Superpowers controller owns discovery, design, planning, review, verification, and pass/fail decisions. Cursor Agent owns every semantic implementation edit and every semantic review-fix edit inside the isolated workspace.

The controller must not edit implementation code or semantic review-fix code during an active overlay workflow. Never implement yourself, patch semantic review findings yourself, or skip review because the change seems small.

### Mechanical review-patch exception

The only controller edit exception is a **mechanical review patch** — deterministic, non-semantic, and limited to the exhaustive allowlist below. Classification is based on edit semantics, not finding severity: **minor** severity or a small line count alone is **not** sufficient to authorize a controller patch.

**Allowlist (exhaustive):**

- formatter output
- whitespace
- a typo in non-executable prose or a comment

**Denylist (never controller-editable):**

- executable code and tests
- configuration and schemas
- dependencies, lockfiles, and generated output
- public APIs
- security, authentication, data, and business logic
- commands and code blocks in documentation

A mechanical patch is allowed only inside the active brief's **allowed files**, with unambiguous ownership and **no scope expansion**. The task remains **`in-review`** while the patch is applied. Record durable **controller-patch** evidence (finding, classification, changed files/diff, controller identity, verification results), rerun the **exact covering verification** commands, and **re-review** the fresh diff before `approved`.

If classification is uncertain, the patch grows beyond the mechanical finding, scope expands, or verification fails, stop and route **one consolidated fix brief** to Cursor through `cursor-agent-bridge`.

One file, a trivial or simple task, a deadline, or the belief that the controller can do it faster are never exceptions for semantic edits. No skip review under pressure.

## Task-start upstream routing

At task start, check whether upstream Superpowers skills are available in the current runtime.

### When upstream Superpowers is unavailable

- Do not block the task. Missing upstream Superpowers is not a blocker.
- Do not insist that upstream Superpowers must be installed.
- Use controller-native planning, review, verification, worktree handling, and branch completion.
- Continue routing every implementation edit and every semantic review-fix edit through `executing-plans-with-cursor`, `reviewing-cursor-changes`, and `cursor-agent-bridge`.

### When upstream Superpowers is available

- Ask the user once for the whole task whether to use upstream Superpowers for discovery, planning, worktrees, verification, and branch completion.
- Do not invoke or route the task through upstream task-specific Superpowers workflows before affirmative confirmation.
- If the user confirms, load and follow the relevant upstream skills for that task (see workflow routing table).
- If the user declines, use controller-native planning, review, verification, worktree handling, and branch completion for that task.
- Honor the explicit user choice for the entire task unless the user changes it.

### Both routes

In both routes, Cursor Agent remains the only semantic implementation and review-fix worker. Every semantic implementation edit and every semantic review-fix edit still routes through `executing-plans-with-cursor`, `reviewing-cursor-changes`, and `cursor-agent-bridge`. Mechanical review patches are the sole controller exception and follow `reviewing-cursor-changes`.

## Workflow routing table

| User intent | Controller loads | Execution route |
| --- | --- | --- |
| Creative or behavioral discovery | `superpowers:brainstorming` | Continue planning; no implementation yet |
| Approved design needs a task plan | `superpowers:writing-plans` | Produce an approved plan only |
| Git repo needs isolation | `superpowers:using-git-worktrees` | Isolate workspace before dispatch |
| Approved plan ready to build | `executing-plans-with-cursor` | Sequential task dispatch through `cursor-agent-bridge` |
| Task worker finished | `reviewing-cursor-changes` | Controller review; semantic fixes route back through `cursor-agent-bridge`; mechanical patches follow the narrow exception |
| Full change set ready to ship | `superpowers:verification-before-completion` | Controller verification only |
| Branch completion | `superpowers:finishing-a-development-branch` | Controller-only; Cursor never finishes the branch |

Reference upstream Superpowers skills for their procedures. Do not duplicate brainstorming, planning, worktree, verification, or branch-finishing guidance in this overlay.

Every semantic implementation edit and every semantic review-fix edit routes through `executing-plans-with-cursor`, `reviewing-cursor-changes`, and `cursor-agent-bridge`. Never call `cursor-agent` directly for task work.

## Controller-only actions

- At task start, check upstream Superpowers availability and honor the once-per-task user choice before routing through upstream workflows.
- Load and follow upstream `superpowers:*` skills for discovery, planning, worktrees, verification, and branch finishing only after the user confirms.
- Otherwise use controller-native planning, review, verification, worktree handling, and branch completion.
- Write task briefs, review briefs, scope decisions, and pass/fail verdicts.
- Inspect run records, reports, diffs, test output, and `HEAD` invariants after every Cursor invocation.
- Apply mechanical review patches only under the allowlist in `reviewing-cursor-changes`; record controller-patch evidence and rerun exact covering verification.
- Block or approve before the next task or final verification.

## Cursor-only actions

- Edit allowed implementation files for the active task.
- Apply semantic review-fix edits from a consolidated review brief.
- Run bounded tests and commands inside the workspace.
- Write the required worker report with verification evidence.

## Hard stop conditions

Stop and refuse if you are about to:

- edit implementation or semantic review-fix code as the controller (mechanical review patches are the sole exception)
- implement yourself because it is one file, trivial, simple, or faster
- skip `reviewing-cursor-changes` because of a deadline
- bypass `executing-plans-with-cursor`, `reviewing-cursor-changes`, or `cursor-agent-bridge`
- copy upstream Superpowers procedures instead of referencing the upstream skill
- trust a worker summary without independent artifact review

Deadline pressure, one-file scope, and simple-task claims are never exceptions to the routing chain.

## Example

User: "Use Superpowers to plan this feature, then implement it quickly yourself because it is only one file."

Required response:

1. Use `superpowers:brainstorming` and `superpowers:writing-plans` until the plan is approved.
2. Refuse controller implementation even for a one-file task.
3. Route execution through `executing-plans-with-cursor`, which dispatches Cursor through `cursor-agent-bridge`.
4. Review with `reviewing-cursor-changes`; send semantic fix-required findings back to Cursor Agent, not to controller edits. Apply only mechanical review patches that pass the allowlist.
5. Finish with `superpowers:verification-before-completion` and `superpowers:finishing-a-development-branch` on the controller side only.
