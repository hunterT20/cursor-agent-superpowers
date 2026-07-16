---
name: using-cursor-superpowers
description: Use when a user wants Superpowers to discover, design, plan, review, or verify work while Cursor Agent performs every implementation and review-fix edit.
---

# Using Cursor Superpowers

## Core role boundary

The Codex or Superpowers controller owns discovery, design, planning, review, verification, and pass/fail decisions. Cursor Agent owns every implementation edit and every review-fix edit inside the isolated workspace.

The controller must not edit implementation code or review-fix code during an active overlay workflow. Never implement yourself, patch review findings yourself, or skip review because the change seems small.

One file, a trivial or simple task, a deadline, or the belief that the controller can do it faster are never exceptions. No skip review under pressure.

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

- Load and follow upstream `superpowers:*` skills for discovery, planning, worktrees, verification, and branch finishing.
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
