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

**Cursor Agent** owns implementation edits and review-fix edits inside the isolated workspace. It runs bounded tests and writes the required worker report.

Cursor must **not** commit, push, merge, rebase, reset, tag, or switch branches.

## End-to-end workflow

1. Use upstream Superpowers skills for discovery, brainstorming, and planning until an implementation plan is approved.
2. Create an isolated git worktree for the change (`superpowers:using-git-worktrees`).
3. Load `executing-plans-with-cursor` and read `references/execution-contracts.md` before the first dispatch.
4. For each plan task, in order:
   1. Write `task-<id>/brief.md` as a regular file on disk before invoking the bridge.
   2. Dispatch **one fresh Cursor session** through `cursor-agent-bridge`.
   3. Wait for the bridge run to finish.
   4. Run `reviewing-cursor-changes` on the run record, worker report, diff, test output, and `HEAD` invariants.
   5. If the verdict is `fix-required`, write one consolidated `review-brief.md` and re-dispatch through the bridge; resume only within that task's review-fix loop when resumable.
   6. Mark the task complete in `progress.md` only after review returns `approved`.
5. After all tasks are approved, run controller-side verification (`superpowers:verification-before-completion`) and branch completion (`superpowers:finishing-a-development-branch`).

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

After validation passes, install the four sibling folders under `skills/` into your Codex skills directory. The default destination is `${CODEX_HOME:-$HOME/.codex}/skills`.

This overlay references upstream `@superpowers` skills (for example `superpowers:brainstorming`, `superpowers:writing-plans`, and `superpowers:using-git-worktrees`). Keep those upstream skills installed and available; this repository does not replace them.

Set `REPO_ROOT` below to the absolute path of your local clone, then run the block as-is:

```bash
REPO_ROOT="/absolute/path/to/cursor-agent-superpowers"
cd "$REPO_ROOT"

SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"

SKILL_NAMES=(
  "using-cursor-superpowers"
  "cursor-agent-bridge"
  "executing-plans-with-cursor"
  "reviewing-cursor-changes"
)

for name in "${SKILL_NAMES[@]}"; do
  src="$REPO_ROOT/skills/$name"
  if [[ ! -d "$src" ]]; then
    echo "ERROR: missing source folder: $src" >&2
    exit 1
  fi
done

for name in "${SKILL_NAMES[@]}"; do
  dest="$SKILLS_DIR/$name"
  if [[ -e "$dest" ]]; then
    echo "ERROR: destination already exists: $dest" >&2
    echo "Back up or remove it intentionally, then rerun." >&2
    exit 1
  fi
done

mkdir -p "$SKILLS_DIR"

for name in "${SKILL_NAMES[@]}"; do
  cp -R "$REPO_ROOT/skills/$name" "$SKILLS_DIR/$name"
done

for name in "${SKILL_NAMES[@]}"; do
  if [[ ! -f "$SKILLS_DIR/$name/SKILL.md" ]]; then
    echo "ERROR: installed skill missing SKILL.md: $SKILLS_DIR/$name" >&2
    exit 1
  fi
done

echo "Installed overlay skills into $SKILLS_DIR"
```

If any destination skill folder already exists, the command stops instead of overwriting it. Handle an existing installation intentionally—for example, back up or remove the destination folder, then rerun the block.

After installation, open a new Codex task or reload Codex if the skill list has not refreshed.

## Branch workflow

Development uses the `agent/cursor-superpowers-overlay` feature branch workflow. Pull requests and merges are handled by the controller, not by Cursor Agent.
