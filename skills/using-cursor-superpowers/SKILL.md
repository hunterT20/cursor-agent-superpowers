---
name: using-cursor-superpowers
description: Use when a user wants a controller to plan, review, or verify work while Cursor Agent performs every implementation and review-fix edit. Upstream Superpowers is optional; when available, ask once per task before routing through upstream workflows.
---

# Using Cursor Superpowers

## Core role boundary

The Codex or Superpowers controller owns discovery, design, planning, review, verification, and pass/fail decisions. Cursor Agent owns every implementation edit and every review-fix edit inside the isolated workspace.

The controller must not edit implementation code or review-fix code during an active overlay workflow. Never implement yourself, patch review findings yourself, or skip review because the change seems small.

One file, a trivial or simple task, a deadline, or the belief that the controller can do it faster are never exceptions. No skip review under pressure.

## Task-start upstream routing

At task start, check whether upstream Superpowers skills are available in the current runtime.

### When upstream Superpowers is unavailable

- Do not block the task. Missing upstream Superpowers is not a blocker.
- Do not insist that upstream Superpowers must be installed.
- Use controller-native planning, review, verification, worktree handling, and branch completion.
- Continue routing every implementation edit and every review-fix edit through `executing-plans-with-cursor`, `reviewing-cursor-changes`, and `cursor-agent-bridge`.

### When upstream Superpowers is available

- Ask the user once for the whole task whether to use upstream Superpowers for discovery, planning, worktrees, verification, and branch completion.
- Do not invoke or route the task through upstream task-specific Superpowers workflows before affirmative confirmation.
- If the user confirms, load and follow the relevant upstream skills for that task (see workflow routing table).
- If the user declines, use controller-native planning, review, verification, worktree handling, and branch completion for that task.
- Honor the explicit user choice for the entire task unless the user changes it.

### Both routes

In both routes, Cursor Agent remains the only implementation and review-fix worker. Every implementation edit and every review-fix edit still routes through `executing-plans-with-cursor`, `reviewing-cursor-changes`, and `cursor-agent-bridge`.

## Workflow routing table

| User intent | Controller loads | Execution route |
| --- | --- | --- |
| Creative or behavioral discovery | `superpowers:brainstorming` | Continue planning; no implementation yet |
| Approved design needs a task plan | `superpowers:writing-plans` | Produce an approved plan only |
| Git repo needs isolation | `superpowers:using-git-worktrees` | Isolate workspace before dispatch |
| Approved plan ready to build | `executing-plans-with-cursor` | Sequential task dispatch through `cursor-agent-bridge` |
| Task worker finished | `reviewing-cursor-changes` | Controller review; fixes route back through `cursor-agent-bridge` |
| Full change set ready to ship | `superpowers:verification-before-completion` | Controller verification only |
| Branch completion | `superpowers:finishing-a-development-branch` | Controller-only; Cursor never finishes the branch |

Reference upstream Superpowers skills for their procedures. Do not duplicate brainstorming, planning, worktree, verification, or branch-finishing guidance in this overlay.

Every implementation edit and every review-fix edit routes through `executing-plans-with-cursor`, `reviewing-cursor-changes`, and `cursor-agent-bridge`. Never call `cursor-agent` directly for task work.

## Controller-only actions

- At task start, check upstream Superpowers availability and honor the once-per-task user choice before routing through upstream workflows.
- Load and follow upstream `superpowers:*` skills for discovery, planning, worktrees, verification, and branch finishing only after the user confirms.
- Otherwise use controller-native planning, review, verification, worktree handling, and branch completion.
- Write task briefs, review briefs, scope decisions, and pass/fail verdicts.
- Inspect run records, reports, diffs, test output, and `HEAD` invariants after every Cursor invocation.
- Block or approve before the next task or final verification.

## Cursor-only actions

- Edit allowed implementation files for the active task.
- Apply review-fix edits from a consolidated review brief.
- Run bounded tests and commands inside the workspace.
- Write the required worker report with verification evidence.

## Hard stop conditions

Stop and refuse if you are about to:

- edit implementation or review-fix code as the controller
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
4. Review with `reviewing-cursor-changes`; send any fix-required findings back to Cursor Agent, not to controller edits.
5. Finish with `superpowers:verification-before-completion` and `superpowers:finishing-a-development-branch` on the controller side only.
