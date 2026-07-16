# Cursor Superpowers Overlay Design

Date: 2026-07-16
Status: Approved

## Goal

Create a four-skill overlay that keeps Superpowers responsible for discovery, brainstorming, planning, review, verification, and branch completion while delegating code changes and test execution to Cursor Agent with model `composer-2.5[fast=false]`.

The overlay must not copy or modify the 14 upstream Superpowers skills. It must compose with them so upstream updates remain usable.

## Roles and authority

### Codex and Superpowers controller

The controller owns:

- Reading project instructions, relevant workspace context, source code, config, and git state.
- Clarifying requirements and producing the approved design and implementation plan.
- Selecting an isolated worktree when the project is a git repository.
- Creating one bounded task brief at a time.
- Reviewing Cursor's report, `git diff`, test evidence, and requirement compliance.
- Deciding whether a task passes, needs another Cursor fix iteration, or is blocked.
- Running fresh final verification and handling branch completion.

The controller must not edit implementation code while this workflow is active. Controller-authored artifacts are limited to plans, task briefs, review briefs, reports, ledgers, and other orchestration files.

### Cursor Agent worker

Cursor Agent may:

- Modify files within the selected workspace and task scope.
- Add or update tests using the project conventions.
- Run read-only inspection commands, formatting, linting, builds, and tests needed by the task.
- Write a structured task report to the path supplied by the controller.

Cursor Agent must not:

- Commit, amend, push, merge, rebase, reset, tag, or switch branches.
- Change files outside the task scope unless it first records a blocker instead of proceeding.
- Rewrite the approved plan or relax acceptance criteria.
- Claim that controller review or final verification has passed.

The controller records the starting `HEAD` and verifies that it is unchanged after every Cursor invocation. An unexpected `HEAD` change is a hard failure that stops the workflow for user direction.

## Overlay skills

### `using-cursor-superpowers`

Entry and routing skill. It activates when the user asks Superpowers to plan or review while Cursor Agent implements. It establishes the role boundary, selects the required upstream Superpowers skills, and routes plan execution into the overlay.

It does not contain a second copy of brainstorming, planning, TDD, worktree, verification, or branch-finishing guidance.

### `cursor-agent-bridge`

Reusable execution boundary around the Cursor CLI. It owns a deterministic script that:

- Validates required commands, workspace, prompt file, and report path.
- Records the pre-run git `HEAD` when git is available.
- Calls `cursor-agent --print --trust --model 'composer-2.5[fast=false]' --workspace "$workspace_path"`.
- Supplies task requirements by file path rather than embedding large artifacts in the command line.
- Captures stdout, stderr, exit status, timing, and available Cursor session metadata.
- Refuses to report success when the required report is missing or empty.
- Detects an unexpected post-run `HEAD` change.
- Produces a machine-readable run record for controller review.

The bridge must use argument arrays and prompt files so shell interpolation cannot execute task text accidentally.

### `executing-plans-with-cursor`

Sequential task orchestrator. It:

- Requires an approved implementation plan.
- Creates or resumes a durable progress ledger.
- Extracts exactly one task brief at a time.
- Starts one fresh Cursor session per task.
- Reuses that task's session for review-fix iterations when a resumable session identifier is available; otherwise it starts a fresh invocation with the task brief and review brief paths.
- Waits for controller review before moving to the next task.
- Never dispatches parallel Cursor implementation tasks in the same worktree.

### `reviewing-cursor-changes`

Controller-side review and fix-loop skill. It checks:

- Starting versus ending `HEAD`.
- Changed-file scope and unexpected generated artifacts.
- Line-by-line task requirement compliance.
- Test-first evidence when the task changes behavior.
- Commands, exit codes, failures, warnings, and omissions in the report.
- Code quality, security, regression risk, and unnecessary scope.

Critical and important findings become a review brief for Cursor. Cursor performs the fix and reruns covering tests. The controller reviews the new diff and evidence again. Minor findings are recorded for final review rather than silently discarded.

## Project workflow

1. Detect the nearest project and load its instructions and minimal relevant context.
2. Use upstream Superpowers brainstorming for creative or behavioral work.
3. Write and obtain approval for the design.
4. Use upstream Superpowers writing-plans to create a task-level implementation plan.
5. Use upstream Superpowers worktree guidance when the project is a git repository and is not already isolated.
6. Record the initial branch and `HEAD`.
7. Create a task brief containing scope, exact requirements, acceptance evidence, allowed files, test commands, and report path.
8. Invoke Cursor through `cursor-agent-bridge`.
9. Inspect the run record, report, git state, diff, and test evidence.
10. If review fails, write one consolidated review brief and send it back to the same task's Cursor session when possible.
11. Mark the task complete in the ledger only after review is clean and evidence is sufficient.
12. Repeat sequentially for the next task.
13. Run upstream Superpowers final verification across the complete change set.
14. Use upstream Superpowers branch-finishing workflow; Cursor never performs this step.

## Task brief contract

Each task brief must contain:

- Task identifier and purpose.
- Exact requirements and constraints copied from the approved plan.
- Allowed workspace and intended file scope.
- Required test-first behavior for feature or bug-fix tasks.
- Acceptance criteria and verification commands.
- Prohibited git and scope-changing actions.
- Report file path and report schema.
- Instruction to stop and report a blocker when requirements conflict or required context is unavailable.

## Cursor report contract

Each report must contain:

- Status: `implemented`, `blocked`, or `failed`.
- Summary of changes.
- Changed files.
- Tests added or modified.
- Commands executed with exit codes and concise results.
- Test-first evidence, including the expected failing result before implementation when applicable.
- Assumptions, unresolved concerns, and out-of-scope discoveries.
- Statement confirming no commit, push, merge, rebase, reset, tag, or branch switch was attempted.

The report is evidence supplied by the worker, not proof of completion. The controller verifies it independently.

## Failure handling

- Missing Cursor CLI or unavailable requested model: stop before modifying the project and report the environmental blocker.
- Cursor exits nonzero: preserve logs and report the task as failed unless the report clearly identifies a recoverable blocker.
- Missing or empty report: fail the invocation even if Cursor stdout sounds successful.
- Unexpected `HEAD` change: stop the workflow; do not reset or rewrite history automatically.
- Out-of-scope changes: reject the task and ask Cursor to revert only its own out-of-scope working-tree changes when ownership is unambiguous; otherwise stop for user direction.
- Test failure: do not mark the task complete; send one consolidated fix brief to Cursor.
- Conflicting plan requirements: stop and ask the user which requirement governs.
- Interrupted session: resume from the durable ledger and verified git state, never from conversation memory alone.

## Safety model

The prompt restriction is not treated as the only control. The workflow combines:

- Worktree isolation when available.
- Explicit file and command scope in each task brief.
- Pre-run and post-run `HEAD` checks.
- Captured execution logs and structured reports.
- Controller inspection of the actual diff.
- No automatic commit, push, merge, reset, or cleanup.

The initial version will not claim operating-system-level containment. If a project requires stronger command isolation, the controller must stop and request an explicitly approved sandbox policy.

## Testing strategy

Each skill is created and verified separately using the skill-authoring RED-GREEN-REFACTOR process:

1. Run a baseline pressure scenario without the new skill and capture the failure mode.
2. Create the minimum skill and any deterministic script needed to address that failure.
3. Validate metadata and structure with the official skill validator.
4. Run the same scenario with the skill and verify compliant behavior.
5. Add only the counters required by observed loopholes, then retest.

The bridge script additionally receives executable tests for:

- Argument validation and paths containing spaces.
- Correct fixed model selection.
- Safe prompt-file handling without shell evaluation.
- Nonzero Cursor exit propagation.
- Missing-report failure.
- Git `HEAD` mutation detection.
- Non-git workspace behavior.

End-to-end validation uses a disposable git fixture, a fake `cursor-agent` executable, and no production project. A final optional smoke test may use the installed Cursor CLI in a disposable fixture without exposing live repositories.

## Packaging

The deliverable is a standalone `cursor-superpowers` directory containing four sibling skill folders. Each skill contains only `SKILL.md`, generated `agents/openai.yaml`, and resources it directly needs. The bridge owns its scripts and tests; other skills reference the bridge by skill name rather than copying scripts.

Installation into `~/.codex/skills` is a separate explicit step after validation so testing cannot accidentally replace an existing personal skill.

## Acceptance criteria

- Four skill folders validate successfully.
- The overlay references upstream Superpowers skills without copying them.
- Every implementation and fix instruction routes through Cursor Agent using the exact model `composer-2.5[fast=false]`.
- No overlay instruction asks Codex to edit implementation code during active execution.
- Cursor is explicitly prohibited from git history and remote mutations.
- The bridge detects changed `HEAD`, missing reports, invalid arguments, and nonzero exits.
- Plan tasks execute sequentially with a durable ledger and review loop.
- Final completion still requires fresh controller-run verification.
- The bundle includes no placeholder files or auxiliary README-style documentation.
