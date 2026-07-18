# cursor-agent-superpowers

A Superpowers overlay where Codex/Superpowers plans and reviews while Cursor Agent implements.

## Skills

| Skill | Responsibility |
| --- | --- |
| `using-cursor-superpowers` | Routes discovery, planning, execution, review, verification, and branch completion to the correct overlay and upstream Superpowers skills. |
| `cursor-agent-bridge` | Runs one bounded implementation or review-fix task through `run_cursor_agent.py` and captures verifiable execution evidence. |
| `executing-plans-with-cursor` | Executes an approved plan sequentially in one isolated worktree, dispatching one Cursor session per task. |
| `reviewing-cursor-changes` | Controller review gate that inspects artifacts, diff, and test evidence before a task is marked complete. |

## Role boundary

The **controller** (Codex or Superpowers) owns discovery, design, planning, review, verification, and branch completion. It writes task and review briefs, inspects run records and diffs, and emits pass/fail verdicts.

**Cursor Agent** owns semantic implementation edits and semantic review-fix edits inside the isolated workspace. It runs bounded tests and writes the required worker report.

The **controller** may apply a narrow **mechanical review patch** during review when a finding is deterministic and non-semantic: only formatter output, whitespace, or a typo in non-executable prose or a comment. **Minor** severity or a small line count alone is **not** enough — classification depends on edit semantics. The controller never patches executable code, tests, configuration, schemas, dependencies, lockfiles, generated output, public APIs, security/authentication/data/business logic, or commands and code blocks in documentation. Patches are limited to the active brief's allowed files, stay **`in-review`** while applied, require durable controller-patch evidence, exact covering verification rerun, and fresh diff re-review before approval. Uncertain, growing, or failed patches route back to Cursor through the bridge.

Cursor must **not** commit, push, merge, rebase, reset, tag, or switch branches.

## End-to-end workflow

1. At task start, the controller checks whether upstream `superpowers:*` skills are available.
   - If unavailable, use controller-native planning, review, verification, and branch completion. Missing upstream Superpowers is not a blocker.
   - If available, ask once for the whole task whether to use upstream Superpowers. Do not route the task through upstream Superpowers workflows before the user confirms.
2. Use upstream Superpowers skills for discovery, brainstorming, and planning when confirmed—or use controller-native planning when upstream is unavailable or declined—until an implementation plan is approved.
3. Create an isolated git worktree for the change (`superpowers:using-git-worktrees` when confirmed, or controller-native worktree isolation when not).
4. Load `executing-plans-with-cursor` and read `references/execution-contracts.md` before the first dispatch.
5. For each plan task, in order:
   1. Write `task-<id>/brief.md` as a regular file on disk before invoking the bridge.
   2. Dispatch **one fresh Cursor session** through `cursor-agent-bridge`.
   3. Wait for the bridge run to finish.
   4. Run `reviewing-cursor-changes` on the run record, worker report, diff, test output, and `HEAD` invariants.
   5. If the verdict is `fix-required`, write one consolidated `review-brief.md` and re-dispatch through the bridge; resume only within that task's review-fix loop when resumable. If a finding qualifies as a mechanical review patch, the controller may patch directly per `reviewing-cursor-changes`, record `controller-patch.md`, rerun exact covering verification, and re-review before approval.
   6. Mark the task complete in `progress.md` only after review returns `approved`.
6. After all tasks are approved, run controller-side verification (`superpowers:verification-before-completion` when confirmed, or controller-native verification when not) and branch completion (`superpowers:finishing-a-development-branch` when confirmed, or controller-native branch completion when not).

Never dispatch parallel implementers. Never advance on a worker success message or bridge exit `0` alone.

## Bridge invocation

The controller writes the task brief in a **separate prior step**. The runner command references only the pre-existing absolute file path. Do not create the brief in the same shell command as the runner (no process substitution, heredocs, or inline task creation).

```bash
python3 skills/cursor-agent-bridge/scripts/run_cursor_agent.py \
  --workspace /absolute/workspace \
  --task-brief /absolute/task-brief.md \
  --report /absolute/report.md \
  --run-record /absolute/run-record.json \
  --stdout-file /absolute/stdout.txt \
  --stderr-file /absolute/stderr.txt
```

All artifact paths must be absolute. The runner always invokes Cursor with model `composer-2.5[fast=false]`.

## Safety notes

- `--force` is used only after the controller verifies worktree isolation and bounded task scope. Do not use the bridge for planning, review, verification, or branch-completion tasks.
- The controller independently verifies the worker report, actual diff, test output, and `HEAD` invariants. Never trust the worker summary alone.
- Bridge exit `0` and worker `STATUS=implemented` are invocation evidence, **not** proof that the task is complete.

## Validation

```bash
python3 -m unittest discover -s tests -v
python3 /Users/chaileasevn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/<skill-name>
```

Run the unittest suite for bridge and contract coverage. Run `quick_validate.py` once per skill folder before installation.

## Installation

After validation passes, install all four overlay skills with the open agent skills CLI:

```bash
npx --yes skills@latest add hunterT20/cursor-agent-superpowers \
  --global \
  --agent codex \
  --skill '*' \
  --copy \
  --yes
```

`npx skills` clones or discovers the repository and installs the four `SKILL.md` folders (`using-cursor-superpowers`, `cursor-agent-bridge`, `executing-plans-with-cursor`, and `reviewing-cursor-changes`). `--global` targets the user-level install, `--agent codex` targets Codex, `--skill '*'` selects all four skills, `--copy` copies files instead of symlinking, and the final `--yes` skips the interactive confirmation. Install all four together—the overlay workflow depends on the bridge, execution, review, and routing skills as a set.

Upstream `@superpowers` skills (for example `superpowers:brainstorming`, `superpowers:writing-plans`, and `superpowers:using-git-worktrees`) are **optional**. The overlay works without them using controller-native planning, review, verification, and branch completion. When upstream Superpowers is available, the controller asks once per task whether to use it and does not route the task through upstream Superpowers workflows before confirmation. The `npx skills` command installs only this repository's four overlay skills, not the upstream `@superpowers` plugin.

Verify the installation:

```bash
npx --yes skills@latest list --global --agent codex
```

To refresh installed skills after upstream changes, run `npx --yes skills@latest update -g`. To remove the overlay skills, run:

```bash
npx --yes skills@latest remove --global --agent codex \
  --skill cursor-agent-bridge executing-plans-with-cursor reviewing-cursor-changes using-cursor-superpowers \
  --yes
```

After installation, open a new Codex task or reload Codex if the skill list has not refreshed.

## Branch workflow

Development uses the `agent/cursor-superpowers-overlay` feature branch workflow. Pull requests and merges are handled by the controller, not by Cursor Agent.
