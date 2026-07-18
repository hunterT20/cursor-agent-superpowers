---
name: reviewing-cursor-changes
description: Use after Cursor Agent implements or fixes a task and before the controller marks that task complete, advances the plan, or performs final verification.
---

# Reviewing Cursor Changes

Controller-side review gate. Read `cursor-agent-bridge` and `executing-plans-with-cursor` for dispatch and ledger rules; reference them, do not copy procedures. The controller must not edit implementation code or apply semantic implementation fixes — Cursor owns semantic fixes. The sole exception is a narrowly defined **mechanical review patch** documented below and in `references/execution-contracts.md`.

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

## Mechanical review-patch exception

Classification is based on edit semantics, not finding severity. **Minor** severity or a small line count alone is **not** sufficient to authorize a controller patch.

The controller may apply a mechanical review patch only when **every** condition holds:

1. The edit is deterministic and non-semantic.
2. It is limited to the exhaustive allowlist: **formatter output**, **whitespace**, or a **typo in non-executable prose or a comment**.
3. The file is already in the active brief's **allowed files**, ownership is unambiguous, and the patch does **not expand scope**.
4. The task remains **`in-review`** while the patch is applied.
5. The controller writes durable **controller-patch** evidence to `.superpowers/cursor-execution/task-<id>/controller-patch.md` recording the **finding**, **classification**, changed files/diff, **controller identity**, and **verification** results.
6. The controller reruns the **exact covering verification** commands from the brief.
7. The controller inspects the fresh diff and **re-review**s before emitting `approved`.

**Never controller-editable (denylist):**

- executable code and tests
- configuration and schemas
- dependencies, lockfiles, and generated output
- public APIs
- security, authentication, data, and business logic
- commands and code blocks in documentation

If classification is **uncertain**, the patch **grows** beyond the mechanical finding, **scope expands**, or **verification fails**, stop patching and route **one consolidated fix brief** through `cursor-agent-bridge`. Do not approve until Cursor returns fresh evidence and the diff passes re-review.

## Consolidated fix brief

Merge all **critical** and **important** findings — and any finding that is not a qualifying mechanical patch — into **one consolidated fix brief**. Route it through `cursor-agent-bridge` (`run_cursor_agent.py`); never apply semantic fixes as the controller. Schema: task id, failing checks, required corrections, allowed files, covering test commands, report path.

## Re-review loop

After Cursor applies semantic fixes and reruns **covering tests**, inspect the new diff and fresh test evidence. **Re-review** before `approved`. After a mechanical review patch, rerun **exact covering verification**, inspect the fresh diff, and **re-review** before `approved`. Repeat until clean or `blocked`. Minor findings do not block alone but must be recorded for **final whole-change review** — never silently discard them.

## Pressure resistance

| Pressure | Required response |
| --- | --- |
| Deadline / move to next task | Refuse; no advance on non-approved verdict |
| Worker report says tests pass | Inspect actual diff and demand exact command, exit code, result |
| Trust the report alone | Reject; verify diff, scope, and evidence independently |
| Controller implements the semantic fix | Refuse; route consolidated fix brief through the bridge |
| Controller patches outside the mechanical allowlist | Refuse; route consolidated fix brief through the bridge |

Deadline pressure, trusting the report alone, and skipping review are **never an exception**.

## Red flags

Stop if you are about to:

- approve with out-of-scope changes or missing test evidence
- check anything before `HEAD` invariants
- emit partial sign-off instead of the three verdict tokens
- advance the ledger or next task after `fix-required` or `blocked`
- run background smoke while review is unresolved
- edit implementation code or apply semantic fixes as Codex/controller (mechanical review patches are the sole exception)
- trust the worker report without the actual diff
