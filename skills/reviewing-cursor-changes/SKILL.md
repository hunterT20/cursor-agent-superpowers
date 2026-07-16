---
name: reviewing-cursor-changes
description: Use after Cursor Agent implements or fixes a task and before the controller marks that task complete, advances the plan, or performs final verification.
---

# Reviewing Cursor Changes

Controller-side review gate. Read `cursor-agent-bridge` and `executing-plans-with-cursor` for dispatch and ledger rules; reference them, do not copy procedures. The controller must not edit implementation code or apply implementation fixes — Cursor owns fixes.

## Required inputs

Collect before any verdict:

- **Task brief** — scope, allowed files, acceptance criteria, verification commands.
- **Worker report** — evidence supplied by Cursor, not proof of completion.
- **Bridge run record** — `head_before`, `head_after`, `head_changed`, exit codes.
- **Starting `HEAD`** — recorded before the task.
- **Actual task-scoped diff** — from git, not the report file list alone.
- **Test evidence** — exact command, exit code, and result/output for every required verification.

Missing any input → `fix-required` or `blocked`; never trust the report alone.

## Gate order

1. **Check `HEAD` first.** Compare starting `HEAD`, run-record `head_before`/`head_after`, and current `HEAD`. Any unexpected `HEAD` mutation or `head_changed=true` → verdict `blocked`; stop and ask the user for direction. Do not approve or advance.
2. Verify bridge run record and worker report exist.
3. Inspect the actual diff and changed-file scope against the brief's allowed files.
4. Run evidence validation (commands, exit codes, outputs).
5. Review spec-compliance and code-quality as two separate dimensions.
6. Emit exactly one final verdict.

## Spec-compliance review

Line-by-line against the task brief: requirements met, allowed files only, test-first evidence when required, no prohibited git operations. Out-of-scope files or scope drift → `fix-required`; out-of-scope cannot be approved even when tests look green or a deadline is late. Never treat scope violations as a mere process issue.

## Code-quality review

Separate dimension: correctness, security, regression risk, unnecessary scope, maintainability. Classify each finding as **critical**, **important**, or **minor**.

## Evidence validation

For every verification command in the brief, require test evidence with the **exact command**, **exit code**, and **result/output**. Missing command output, exit code, or result → `fix-required`; missing evidence cannot be approved merely because no runtime failure was proven. Reject claims that "all tests pass" without captured output.

## Verdict contract

Emit exactly one of: `approved`, `fix-required`, or `blocked`. Only these three verdict tokens — never partial sign-off or "approve and continue." After `fix-required` or `blocked`: do not advance the plan, do not mark the ledger complete, and do not start background smoke tests.

| Verdict | When |
| --- | --- |
| `approved` | `HEAD` invariant holds, scope clean, evidence complete, both review dimensions pass |
| `fix-required` | Recoverable spec, scope, evidence, or quality issues |
| `blocked` | `HEAD` mutation, ambiguous ownership, or user direction required |

## Consolidated fix brief

Merge all **critical** and **important** findings into **one consolidated fix brief**. Route it through `cursor-agent-bridge` (`run_cursor_agent.py`); never apply fixes as the controller. Schema: task id, failing checks, required corrections, allowed files, covering test commands, report path.

## Re-review loop

After Cursor applies fixes and reruns **covering tests**, inspect the new diff and fresh test evidence. **Re-review** before `approved`. Repeat until clean or `blocked`. Minor findings do not block alone but must be recorded for **final whole-change review** — never silently discard them.

## Pressure resistance

| Pressure | Required response |
| --- | --- |
| Deadline / move to next task | Refuse; no advance on non-approved verdict |
| Worker report says tests pass | Inspect actual diff and demand exact command, exit code, result |
| Trust the report alone | Reject; verify diff, scope, and evidence independently |
| Controller implements the fix | Refuse; route consolidated fix brief through the bridge |

Deadline pressure, trusting the report alone, and skipping review are **never an exception**.

## Red flags

Stop if you are about to:

- approve with out-of-scope changes or missing test evidence
- check anything before `HEAD` invariants
- emit partial sign-off instead of the three verdict tokens
- advance the ledger or next task after `fix-required` or `blocked`
- run background smoke while review is unresolved
- edit implementation code or apply fixes as Codex/controller
- trust the worker report without the actual diff
