# Optional Superpowers Routing Implementation Plan

> **For agentic workers:** REQUIRED EXECUTION CONTRACT: Cursor Agent performs all implementation edits through `cursor-agent-bridge`; the controller owns the brief, review, verification, and pass/fail decision.

**Goal:** Make upstream Superpowers optional and require one user confirmation per task when it is available.

**Architecture:** Keep the four-skill overlay and controller/worker boundary unchanged. Modify only the entry routing contract, metadata, tests, and README so the controller can use native capabilities when upstream Superpowers is absent or declined.

**Tech Stack:** Markdown Agent Skills, YAML UI metadata, Python `unittest`.

## Global Constraints

- Cursor Agent remains the only implementation and review-fix editor.
- Do not change `cursor-agent-bridge`, `executing-plans-with-cursor`, or `reviewing-cursor-changes`.
- Do not change the fixed Cursor model or git restrictions.
- Ask about upstream Superpowers once per task, only when it is available.
- Missing upstream Superpowers must fall back to controller-native planning, review, verification, and branch completion without blocking.

---

### Task 1: Optional upstream Superpowers routing

**Files:**

- Modify: `skills/using-cursor-superpowers/SKILL.md`
- Modify: `skills/using-cursor-superpowers/agents/openai.yaml`
- Modify: `tests/test_skill_contracts.py`
- Modify: `README.md`

**Interfaces:**

- Consumes: availability of upstream `superpowers:*` skills and the user's once-per-task choice.
- Produces: either confirmed upstream routing or controller-native planning/review/verification, with Cursor implementation unchanged.

- [ ] **Step 1: Write failing contract tests**

Add tests in `UsingCursorSuperpowersContractTests` requiring the skill to:

- detect whether upstream Superpowers is available;
- use controller-native planning, review, verification, and branch completion when unavailable;
- ask once per task when available and avoid loading upstream skills before confirmation;
- honor confirmed use or confirmed native handling for the whole task;
- preserve the mandatory Cursor implementation/review-fix chain.

Update the exact frontmatter-description expectation if the description changes.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python3 -m unittest tests.test_skill_contracts.UsingCursorSuperpowersContractTests -v
```

Expected: FAIL because optional availability and confirmation routing are not documented yet.

- [ ] **Step 3: Implement the minimal routing contract**

Update `SKILL.md` with a short startup decision:

1. Check upstream skill availability.
2. If unavailable, use controller-native capabilities.
3. If available, ask once for the task and load upstream skills only after confirmation.
4. Preserve Cursor-only implementation and mandatory overlay review.

Update `agents/openai.yaml` so its prompt does not imply upstream Superpowers is mandatory.

- [ ] **Step 4: Update README dependency guidance**

State that the four overlay skills are installed together, upstream Superpowers is optional, and the controller asks once when it is available.

- [ ] **Step 5: Run focused and full verification**

Run:

```bash
python3 -m unittest tests.test_skill_contracts.UsingCursorSuperpowersContractTests -v
python3 -m unittest discover -s tests -v
```

Expected: all tests PASS.

- [ ] **Step 6: Validate the changed skill**

Run:

```bash
uv run --quiet --with pyyaml python /Users/chaileasevn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/using-cursor-superpowers
git diff --check
```

Expected: validator and diff check exit `0`.
