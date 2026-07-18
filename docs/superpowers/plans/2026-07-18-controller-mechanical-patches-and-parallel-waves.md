# Controller Mechanical Patches and Parallel Waves Implementation Plan

> **For agentic workers:** REQUIRED EXECUTION CONTRACT: Cursor Agent performs implementation edits through `cursor-agent-bridge`; the controller owns briefs, reviews, mechanical review-patch exceptions, verification, commits, integration, and pass/fail decisions.

**Goal:** Add a safe controller mechanical-patch exception and dependency-proven parallel Cursor waves in separate worktrees.

**Architecture:** Preserve Cursor ownership of semantic implementation and review-fix work. Add a narrow, evidence-backed controller exception for deterministic non-semantic review edits. Keep sequential execution as the default while permitting explicit dependency-free waves whose independently reviewed branches are integrated one at a time.

**Tech Stack:** Markdown Agent Skills, Python `unittest`, Git worktrees.

## Global constraints

- `minor` severity alone never authorizes a controller edit.
- Controller patches are limited to the design allowlist and must be recorded, re-verified, and re-reviewed.
- Any semantic or ambiguous finding returns to Cursor through `cursor-agent-bridge`.
- Parallel tasks never share a worktree, branch, Cursor session, artifact root, or mutable integration surface.
- Cursor never commits, pushes, merges, rebases, resets, tags, or switches branches.
- The bridge runner and fixed model remain unchanged.

---

### Task 1: Controller mechanical review-patch contract

**Files:**

- Modify: `skills/using-cursor-superpowers/SKILL.md`
- Modify: `skills/reviewing-cursor-changes/SKILL.md`
- Modify: `skills/executing-plans-with-cursor/references/execution-contracts.md`
- Modify: `tests/test_skill_contracts.py`
- Modify: `README.md`

**Interfaces:**

- Consumes: a controller review finding plus active task brief, diff, and verification evidence.
- Produces: either a recorded mechanical controller patch with fresh verification, or a consolidated Cursor fix brief.

- [ ] **Step 1: Write failing contract tests**

Replace blanket controller-fix assertions with tests requiring:

- a semantics-based allowlist: formatter output, whitespace, typo in non-executable prose/comment;
- a denylist covering executable code, tests, config, schema, dependency/lockfile/generated output, public API, security/auth/data/business logic, and executable documentation snippets;
- allowed-file and no-scope-expansion gates;
- durable controller-patch evidence, exact covering verification, and re-review before approval;
- fallback to Cursor on ambiguity, growth, or verification failure.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
python3 -m unittest \
  tests.test_skill_contracts.UsingCursorSuperpowersContractTests \
  tests.test_skill_contracts.ReviewingCursorChangesContractTests -v
```

Expected: FAIL because the current contract forbids all controller review-fix edits.

- [ ] **Step 3: Implement the minimal skill contract**

Update the entry and review skills plus execution artifact reference. Preserve Cursor-only semantic edits and all existing review gates.

- [ ] **Step 4: Update README**

Explain the exception in plain language and make clear that severity and line count are not sufficient.

- [ ] **Step 5: Verify task**

```bash
python3 -m unittest \
  tests.test_skill_contracts.UsingCursorSuperpowersContractTests \
  tests.test_skill_contracts.ReviewingCursorChangesContractTests -v
python3 -m unittest discover -s tests -v
```

Expected: PASS.

---

### Task 2: Dependency-proven parallel isolated waves

**Files:**

- Modify: `skills/executing-plans-with-cursor/SKILL.md`
- Modify: `skills/executing-plans-with-cursor/references/execution-contracts.md`
- Modify: `tests/test_skill_contracts.py`
- Modify: `README.md`

**Interfaces:**

- Consumes: an approved plan with explicit dependency graph and intended write sets.
- Produces: sequential execution by default, or bounded isolated task branches that become complete only after sequential integration and verification.

- [ ] **Step 1: Write failing contract tests**

Replace unconditional no-parallel assertions with tests requiring:

- sequential-by-default and ambiguity-to-sequential routing;
- no dependency edge, disjoint write sets, and no shared integration-sensitive contracts;
- separate worktree/branch/session/artifact root/ledger and `HEAD` invariant per task;
- concurrency cap of three;
- `approved-isolated` before integration;
- controller-owned commits and sequential integration;
- affected tests after each integration and the full suite after each wave;
- later waves from the updated integration `HEAD`;
- stop and sequential fallback on overlap, `HEAD` mutation, conflict, or integration failure.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
python3 -m unittest tests.test_skill_contracts.ExecutingPlansWithCursorContractTests -v
```

Expected: FAIL because the current contract forbids parallel execution even for proven-independent tasks.

- [ ] **Step 3: Implement execution and artifact contracts**

Update the execution skill and reference with a short routing decision, an isolated-wave loop, integration gate, and blocker behavior. Keep the existing sequential loop as the default path.

- [ ] **Step 4: Update README**

Describe the safe parallel path and emphasize that file disjointness alone is insufficient.

- [ ] **Step 5: Run focused and full verification**

```bash
python3 -m unittest tests.test_skill_contracts.ExecutingPlansWithCursorContractTests -v
python3 -m unittest discover -s tests -v
```

Expected: PASS.

---

### Task 3: Final validation

**Files:**

- Verify only unless a consolidated Cursor fix brief is required.

- [ ] **Step 1: Validate changed skills**

```bash
uv run --quiet --with pyyaml python /Users/chaileasevn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/using-cursor-superpowers
uv run --quiet --with pyyaml python /Users/chaileasevn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/executing-plans-with-cursor
uv run --quiet --with pyyaml python /Users/chaileasevn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/reviewing-cursor-changes
uv run --quiet --with pyyaml python /Users/chaileasevn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/cursor-agent-bridge
git diff --check
```

Expected: every command exits `0`.

- [ ] **Step 2: Review final whole-change diff**

Confirm the two contracts do not weaken `HEAD`, scope, evidence, worker git, bridge, or semantic-review boundaries.
