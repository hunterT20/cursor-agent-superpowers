#!/usr/bin/env python3
"""Static contract tests for overlay skill metadata and authority boundaries."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
USING_CURSOR_SUPERPOWERS = REPO_ROOT / "skills" / "using-cursor-superpowers" / "SKILL.md"

EXPECTED_NAME = "using-cursor-superpowers"
EXPECTED_DESCRIPTION = (
    "Use when a user wants Superpowers to discover, design, plan, review, or verify work "
    "while Cursor Agent performs every implementation and review-fix edit."
)

REQUIRED_UPSTREAM_SKILLS = (
    "superpowers:brainstorming",
    "superpowers:writing-plans",
    "superpowers:using-git-worktrees",
    "superpowers:verification-before-completion",
    "superpowers:finishing-a-development-branch",
)

REQUIRED_OVERLAY_SKILLS = (
    "executing-plans-with-cursor",
    "reviewing-cursor-changes",
    "cursor-agent-bridge",
)

REQUIRED_BODY_SECTIONS = (
    "role boundary",
    "routing",
    "controller-only",
    "cursor-only",
    "hard stop",
    "example",
)

PRESSURE_PHRASES = (
    "one file",
    "one-file",
    "trivial",
    "simple task",
    "deadline",
    "faster",
    "skip review",
    "controller implement",
)

NEVER_EXCEPTION_PATTERNS = (
    r"never\s+(an?\s+)?exception",
    r"no\s+exception",
    r"never\s+skip",
    r"never\s+shortcut",
)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse YAML-like frontmatter without external dependencies."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        raise ValueError("Missing YAML frontmatter delimited by ---")
    frontmatter_block = match.group(1)
    body = text[match.end() :]
    frontmatter: dict[str, str] = {}
    for line in frontmatter_block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition(":")
        if not key or not value.strip():
            raise ValueError(f"Invalid frontmatter line: {line!r}")
        frontmatter[key.strip()] = value.strip()
    return frontmatter, body


def load_skill() -> tuple[dict[str, str], str, str]:
    text = USING_CURSOR_SUPERPOWERS.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    combined = f"{frontmatter.get('description', '')}\n{body}".lower()
    return frontmatter, body, combined


class UsingCursorSuperpowersContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frontmatter, cls.body, cls.combined = load_skill()

    def test_skill_file_exists(self) -> None:
        self.assertTrue(USING_CURSOR_SUPERPOWERS.is_file())

    def test_frontmatter_has_only_name_and_description(self) -> None:
        self.assertEqual(set(self.frontmatter.keys()), {"name", "description"})

    def test_frontmatter_name(self) -> None:
        self.assertEqual(self.frontmatter["name"], EXPECTED_NAME)

    def test_description_starts_with_use_when(self) -> None:
        self.assertTrue(self.frontmatter["description"].startswith("Use when"))

    def test_frontmatter_description_exact(self) -> None:
        self.assertEqual(self.frontmatter["description"], EXPECTED_DESCRIPTION)

    def test_names_required_upstream_skills(self) -> None:
        for skill in REQUIRED_UPSTREAM_SKILLS:
            with self.subTest(skill=skill):
                self.assertIn(skill, self.combined)

    def test_requires_overlay_execution_skills(self) -> None:
        for skill in ("executing-plans-with-cursor", "reviewing-cursor-changes"):
            with self.subTest(skill=skill):
                self.assertIn(skill, self.combined)

    def test_routes_through_cursor_agent_bridge(self) -> None:
        self.assertIn("cursor-agent-bridge", self.combined)

    def test_codex_must_not_edit_implementation_code(self) -> None:
        patterns = (
            r"codex.*must not.*edit",
            r"controller.*must not.*edit",
            r"never edit.*implementation",
            r"must not edit.*implementation",
            r"does not edit.*implementation",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must state Codex/controller must not edit implementation code",
        )

    def test_codex_must_not_edit_review_fix_code(self) -> None:
        patterns = (
            r"review-fix",
            r"review fix",
            r"fix edits",
        )
        self.assertTrue(
            any(term in self.combined for term in patterns),
            "Skill must mention review-fix edits as Cursor-only work",
        )
        deny_patterns = (
            r"controller.*must not.*review-fix",
            r"codex.*must not.*review-fix",
            r"never.*review-fix.*edit",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in deny_patterns)
            or "review-fix edit" in self.combined,
            "Skill must forbid controller review-fix edits",
        )

    def test_routes_implementation_to_cursor_agent(self) -> None:
        patterns = (
            r"cursor agent.*implementation",
            r"implementation.*cursor agent",
            r"delegate.*implementation.*cursor",
            r"routes?.*implementation.*cursor",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must route implementation edits to Cursor Agent",
        )

    def test_routes_fix_edits_to_cursor_agent(self) -> None:
        patterns = (
            r"fix.*cursor agent",
            r"cursor agent.*fix",
            r"review-fix.*cursor",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must route review-fix edits to Cursor Agent",
        )

    def test_every_implementation_and_fix_routes_through_overlay_chain(self) -> None:
        for skill in REQUIRED_OVERLAY_SKILLS:
            with self.subTest(skill=skill):
                self.assertIn(skill, self.combined)

    def test_upstream_skills_referenced_not_copied(self) -> None:
        reference_patterns = (
            r"reference",
            r"do not duplicate",
            r"not duplicate",
            r"upstream",
            r"read the",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in reference_patterns),
            "Skill must instruct referencing upstream skills instead of copying procedures",
        )
        self.assertNotIn("[todo:", self.combined)

    def test_required_body_sections_present(self) -> None:
        for section in REQUIRED_BODY_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, self.combined)

    def test_pressure_resistance_one_file_never_exception(self) -> None:
        self.assertTrue(
            "one file" in self.combined or "one-file" in self.combined,
            "Skill must address one-file pressure explicitly",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in NEVER_EXCEPTION_PATTERNS),
            "Skill must state pressure scenarios are never exceptions",
        )

    def test_pressure_resistance_trivial_simple_never_exception(self) -> None:
        self.assertTrue(
            "trivial" in self.combined or "simple" in self.combined,
            "Skill must address trivial/simple task pressure",
        )

    def test_pressure_resistance_deadline_never_exception(self) -> None:
        self.assertIn("deadline", self.combined)

    def test_pressure_resistance_controller_faster_never_exception(self) -> None:
        faster_patterns = (
            r"faster",
            r"controller can do it",
            r"do it yourself",
            r"implement.*yourself",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in faster_patterns),
            "Skill must counter 'controller can do it faster' pressure",
        )

    def test_no_skip_review_under_pressure(self) -> None:
        skip_patterns = (
            r"skip.*review",
            r"never skip",
            r"no skip",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in skip_patterns),
            "Skill must forbid skipping review under pressure",
        )

    def test_no_todo_placeholders_remain(self) -> None:
        self.assertNotRegex(self.body, r"\[TODO", msg="SKILL.md still contains TODO placeholders")


EXECUTING_PLANS_WITH_CURSOR = REPO_ROOT / "skills" / "executing-plans-with-cursor" / "SKILL.md"
EXECUTION_CONTRACTS_REFERENCE = (
    REPO_ROOT / "skills" / "executing-plans-with-cursor" / "references" / "execution-contracts.md"
)

EXECUTION_EXPECTED_NAME = "executing-plans-with-cursor"
EXECUTION_EXPECTED_DESCRIPTION = (
    "Use when an approved implementation plan must be executed task-by-task by "
    "Cursor Agent inside one isolated project workspace."
)

EXECUTION_REQUIRED_BODY_SECTIONS = (
    "prerequisite",
    "sequential",
    "session rule",
    "red flag",
)

EXECUTION_COMBINED_BODY_SECTIONS = (
    "artifact layout",
    "task-brief",
    "progress ledger",
    "blocker",
)

TASK_BRIEF_SCHEMA_FIELDS = (
    "task identifier",
    "purpose",
    "exact requirements",
    "allowed workspace",
    "file scope",
    "test-first",
    "acceptance criteria",
    "verification command",
    "prohibited git",
    "report file path",
    "report schema",
    "blocker",
)


def load_execution_skill() -> tuple[dict[str, str], str, str, str, str]:
    text = EXECUTING_PLANS_WITH_CURSOR.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    combined = f"{frontmatter.get('description', '')}\n{body}".lower()
    reference = ""
    if EXECUTION_CONTRACTS_REFERENCE.is_file():
        reference = EXECUTION_CONTRACTS_REFERENCE.read_text(encoding="utf-8")
    full_combined = f"{combined}\n{reference}".lower()
    return frontmatter, body, combined, reference, full_combined


class ExecutingPlansWithCursorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frontmatter, cls.body, cls.combined, cls.reference, cls.full_combined = (
            load_execution_skill()
        )

    def test_skill_file_exists(self) -> None:
        self.assertTrue(EXECUTING_PLANS_WITH_CURSOR.is_file())

    def test_execution_contracts_reference_exists(self) -> None:
        self.assertTrue(
            EXECUTION_CONTRACTS_REFERENCE.is_file(),
            "references/execution-contracts.md must exist for progressive disclosure",
        )

    def test_requires_reading_contracts_reference_before_first_dispatch(self) -> None:
        patterns = (
            r"references/execution-contracts\.md",
            r"execution-contracts\.md",
        )
        read_before_patterns = (
            r"read.*execution-contracts.*before.*first\s+dispatch",
            r"read.*references/execution-contracts.*before.*dispatch",
            r"before.*first\s+dispatch.*read.*execution-contracts",
            r"must\s+read.*execution-contracts.*before",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "SKILL.md must name references/execution-contracts.md",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in read_before_patterns),
            "SKILL.md must require reading execution-contracts before first dispatch",
        )

    def test_frontmatter_has_only_name_and_description(self) -> None:
        self.assertEqual(set(self.frontmatter.keys()), {"name", "description"})

    def test_frontmatter_name(self) -> None:
        self.assertEqual(self.frontmatter["name"], EXECUTION_EXPECTED_NAME)

    def test_description_starts_with_use_when(self) -> None:
        self.assertTrue(self.frontmatter["description"].startswith("Use when"))

    def test_frontmatter_description_exact(self) -> None:
        self.assertEqual(self.frontmatter["description"], EXECUTION_EXPECTED_DESCRIPTION)

    def test_requires_approved_plan_before_dispatch(self) -> None:
        patterns = (
            r"approved\s+(implementation\s+)?plan",
            r"plan\s+must\s+be\s+approved",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must require an approved plan before dispatch",
        )

    def test_requires_isolated_worktree_before_dispatch(self) -> None:
        patterns = (
            r"isolated\s+worktree",
            r"worktree\s+isolation",
            r"isolated\s+workspace",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must require an isolated worktree before dispatch",
        )

    def test_artifact_root_is_cursor_execution(self) -> None:
        self.assertIn(".superpowers/cursor-execution/", self.full_combined)

    def test_progress_ledger_path(self) -> None:
        self.assertIn("progress.md", self.full_combined)
        ledger_patterns = (
            r"progress\.md",
            r"progress ledger",
            r"durable ledger",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in ledger_patterns),
            "Skill must define progress.md as the durable ledger",
        )

    def test_one_fresh_cursor_session_per_task(self) -> None:
        patterns = (
            r"one\s+fresh\s+cursor\s+session\s+per\s+task",
            r"fresh\s+cursor\s+session.*per\s+task",
            r"one\s+fresh\s+session\s+per\s+task",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must start one fresh Cursor session per task",
        )

    def test_resume_only_within_task_review_fix_loop(self) -> None:
        patterns = (
            r"resume.*review-fix",
            r"resume.*same\s+task",
            r"review-fix.*resume",
            r"resume.*only.*task",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must allow resume only within the active task's review-fix loop",
        )

    def test_sequential_implementation_in_shared_worktree(self) -> None:
        self.assertIn("sequential", self.combined)
        shared_patterns = (
            r"shared\s+worktree",
            r"one\s+worktree",
            r"same\s+worktree",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in shared_patterns),
            "Skill must implement sequentially in a shared worktree",
        )

    def test_never_parallel_implementers(self) -> None:
        deny_patterns = (
            r"never\s+parallel",
            r"no\s+parallel",
            r"not\s+parallel",
            r"never\s+dispatch\s+parallel",
            r"never\s+fan-out",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in deny_patterns),
            "Skill must forbid parallel Cursor implementers",
        )
        self.assertIn("parallel", self.combined)

    def test_independent_tasks_still_sequential(self) -> None:
        patterns = (
            r"independent.*sequential",
            r"sequential.*independent",
            r"even\s+when.*independent",
            r"independent.*never\s+parallel",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must keep independent tasks sequential, never parallel",
        )

    def test_task_brief_schema_fields_present(self) -> None:
        for field in TASK_BRIEF_SCHEMA_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, self.full_combined)

    def test_routes_through_cursor_agent_bridge(self) -> None:
        self.assertIn("cursor-agent-bridge", self.combined)
        bridge_patterns = (
            r"run_cursor_agent\.py",
            r"cursor-agent-bridge",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in bridge_patterns),
            "Skill must dispatch through cursor-agent-bridge",
        )

    def test_never_direct_cursor_agent_cli(self) -> None:
        patterns = (
            r"never\s+call\s+`?cursor-agent`?",
            r"not\s+call\s+`?cursor-agent`?",
            r"never.*direct.*cursor-agent",
            r"do not call\s+`?cursor-agent`?",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must forbid direct cursor-agent CLI invocation",
        )

    def test_requires_review_before_ledger_completion(self) -> None:
        self.assertIn("reviewing-cursor-changes", self.combined)
        review_patterns = (
            r"reviewing-cursor-changes.*before.*ledger",
            r"before.*ledger.*reviewing-cursor-changes",
            r"reviewing-cursor-changes.*before.*complete",
            r"before.*mark.*complete.*reviewing-cursor-changes",
            r"reviewing-cursor-changes.*before.*next\s+task",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in review_patterns),
            "Skill must require reviewing-cursor-changes before ledger completion or next task",
        )

    def test_worker_exit_zero_is_not_completion(self) -> None:
        patterns = (
            r"exit\s+`?0`?.*not.*complet",
            r"exit\s+0.*not.*complet",
            r"not.*proof.*complet",
            r"not.*task.*complet",
            r"success.*not.*complet",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must state worker exit 0 is not task completion",
        )

    def test_resume_from_ledger_and_git_state_not_memory(self) -> None:
        self.assertIn("ledger", self.combined)
        memory_patterns = (
            r"not.*conversation\s+memory",
            r"never.*conversation\s+memory",
            r"conversation\s+memory\s+alone",
        )
        git_patterns = (
            r"git\s+state",
            r"verified\s+git",
            r"head",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in memory_patterns),
            "Skill must not resume from conversation memory alone",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in git_patterns),
            "Skill must resume from verified git state",
        )

    def test_codex_must_not_edit_implementation(self) -> None:
        patterns = (
            r"codex.*must not.*edit",
            r"controller.*must not.*edit",
            r"never edit.*implementation",
            r"must not edit.*implementation",
            r"does not edit.*implementation",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must forbid Codex/controller implementation edits",
        )

    def test_required_body_sections_present(self) -> None:
        for section in EXECUTION_REQUIRED_BODY_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, self.combined)

    def test_combined_reference_body_sections_present(self) -> None:
        for section in EXECUTION_COMBINED_BODY_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, self.full_combined)

    def test_pressure_resistance_parallel_workers_never_exception(self) -> None:
        parallel_patterns = (
            r"parallel",
            r"fan-out",
            r"fan out",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in parallel_patterns),
            "Skill must address parallel-worker pressure",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in NEVER_EXCEPTION_PATTERNS),
            "Skill must state parallel pressure is never an exception",
        )

    def test_pressure_resistance_trust_success_message(self) -> None:
        patterns = (
            r"success\s+message",
            r"trust.*success",
            r"worker.*summary",
            r"implemented.*not.*complet",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must reject trusting worker success messages as completion",
        )

    def test_pressure_resistance_skip_review(self) -> None:
        skip_patterns = (
            r"skip.*review",
            r"never skip",
            r"no skip",
            r"before.*next\s+task.*review",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in skip_patterns),
            "Skill must forbid skipping review before advancing",
        )

    def test_references_dependencies_not_copies(self) -> None:
        reference_patterns = (
            r"reference",
            r"read the",
            r"required sub-skill",
            r"do not copy",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in reference_patterns),
            "Skill must reference dependency skills instead of copying procedures",
        )

    def test_no_todo_placeholders_remain(self) -> None:
        self.assertNotRegex(self.body, r"\[TODO", msg="SKILL.md still contains TODO placeholders")


REVIEWING_CURSOR_CHANGES = REPO_ROOT / "skills" / "reviewing-cursor-changes" / "SKILL.md"

REVIEW_EXPECTED_NAME = "reviewing-cursor-changes"
REVIEW_EXPECTED_DESCRIPTION = (
    "Use after Cursor Agent implements or fixes a task and before the controller "
    "marks that task complete, advances the plan, or performs final verification."
)

REVIEW_REQUIRED_BODY_SECTIONS = (
    "required input",
    "gate order",
    "spec-compliance",
    "code-quality",
    "evidence validation",
    "verdict contract",
    "consolidated fix brief",
    "re-review loop",
    "red flag",
)

REVIEW_REQUIRED_INPUTS = (
    "task brief",
    "worker report",
    "run record",
    "head",
    "diff",
    "test evidence",
)


def load_review_skill() -> tuple[dict[str, str], str, str]:
    text = REVIEWING_CURSOR_CHANGES.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    combined = f"{frontmatter.get('description', '')}\n{body}".lower()
    return frontmatter, body, combined


class ReviewingCursorChangesContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frontmatter, cls.body, cls.combined = load_review_skill()

    def test_skill_file_exists(self) -> None:
        self.assertTrue(REVIEWING_CURSOR_CHANGES.is_file())

    def test_frontmatter_has_only_name_and_description(self) -> None:
        self.assertEqual(set(self.frontmatter.keys()), {"name", "description"})

    def test_frontmatter_name(self) -> None:
        self.assertEqual(self.frontmatter["name"], REVIEW_EXPECTED_NAME)

    def test_description_starts_with_use_when(self) -> None:
        self.assertTrue(self.frontmatter["description"].startswith("Use when") or self.frontmatter["description"].startswith("Use after"))

    def test_frontmatter_description_exact(self) -> None:
        self.assertEqual(self.frontmatter["description"], REVIEW_EXPECTED_DESCRIPTION)

    def test_required_inputs_present(self) -> None:
        for item in REVIEW_REQUIRED_INPUTS:
            with self.subTest(item=item):
                self.assertIn(item, self.combined)

    def test_checks_head_before_other_approval_decisions(self) -> None:
        head_first_patterns = (
            r"head.*first",
            r"first.*head",
            r"before.*other.*approval.*head",
            r"check.*head.*before",
            r"gate.*head",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in head_first_patterns),
            "Skill must check HEAD before any other approval decision",
        )

    def test_head_mutation_is_blocked(self) -> None:
        self.assertIn("blocked", self.combined)
        mutation_patterns = (
            r"head.*mutat",
            r"mutat.*head",
            r"head.*chang",
            r"head_changed",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in mutation_patterns),
            "Skill must treat HEAD mutation as blocked",
        )

    def test_separate_spec_compliance_and_code_quality(self) -> None:
        self.assertIn("spec-compliance", self.combined)
        self.assertIn("code-quality", self.combined)
        separate_patterns = (
            r"separate.*spec",
            r"spec.*separate",
            r"two.*dimension",
            r"spec-compliance.*code-quality",
            r"code-quality.*spec-compliance",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in separate_patterns),
            "Skill must separate spec-compliance and code-quality review",
        )

    def test_inspects_actual_diff_not_report_alone(self) -> None:
        diff_patterns = (
            r"actual diff",
            r"task-scoped diff",
            r"inspect.*diff",
            r"never trust.*report",
            r"not trust.*report",
            r"do not trust.*report",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in diff_patterns),
            "Skill must inspect actual diff and not trust the report alone",
        )

    def test_verifies_changed_file_scope(self) -> None:
        scope_patterns = (
            r"changed-file scope",
            r"file scope",
            r"out-of-scope",
            r"out of scope",
            r"allowed files",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in scope_patterns),
            "Skill must verify changed-file scope against the brief",
        )

    def test_requires_test_command_exit_code_and_result(self) -> None:
        self.assertIn("exit code", self.combined)
        evidence_patterns = (
            r"test evidence",
            r"command.*exit code",
            r"exit code.*result",
            r"exact command",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in evidence_patterns),
            "Skill must require test command, exit code, and result evidence",
        )

    def test_exact_verdict_contract(self) -> None:
        for verdict in ("approved", "fix-required", "blocked"):
            with self.subTest(verdict=verdict):
                self.assertIn(verdict, self.combined)
        deny_patterns = (
            r"conditional.*approv",
            r"approv.*with.*note",
            r"approv.*có điều kiện",
            r"with-notes",
        )
        self.assertFalse(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in deny_patterns),
            "Skill must not allow conditional or with-notes approval",
        )

    def test_missing_evidence_cannot_be_approved(self) -> None:
        patterns = (
            r"missing evidence.*not.*approv",
            r"not.*approv.*missing evidence",
            r"missing evidence.*fix-required",
            r"cannot.*approv.*missing",
            r"unproven.*not.*approv",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must not approve missing evidence because runtime failure is unproven",
        )

    def test_out_of_scope_cannot_be_approved(self) -> None:
        patterns = (
            r"out-of-scope.*not.*approv",
            r"out of scope.*not.*approv",
            r"out-of-scope.*fix-required",
            r"cannot.*approv.*out-of-scope",
            r"scope.*not.*approv",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must not approve out-of-scope changes",
        )

    def test_consolidated_fix_brief_through_bridge(self) -> None:
        self.assertIn("consolidated fix brief", self.combined)
        self.assertIn("cursor-agent-bridge", self.combined)
        bridge_patterns = (
            r"consolidat.*fix brief.*cursor-agent-bridge",
            r"cursor-agent-bridge.*consolidat",
            r"fix brief.*bridge",
            r"route.*cursor-agent-bridge",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in bridge_patterns),
            "Skill must route consolidated fix brief through cursor-agent-bridge",
        )

    def test_requires_covering_tests_and_rereview(self) -> None:
        patterns = (
            r"covering test",
            r"re-review",
            r"re-review.*before.*approv",
            r"review again",
            r"rerun.*test.*review",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must require covering tests and re-review before approval",
        )

    def test_minor_findings_recorded_not_discarded(self) -> None:
        minor_patterns = (
            r"minor finding",
            r"final whole-change review",
            r"final review",
            r"never.*discard",
            r"not.*silently discard",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in minor_patterns),
            "Skill must record minor findings for final whole-change review",
        )

    def test_controller_must_not_apply_fixes(self) -> None:
        patterns = (
            r"controller.*must not.*edit",
            r"codex.*must not.*edit",
            r"never.*apply.*fix",
            r"must not.*implementation fix",
            r"does not edit.*implementation",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must forbid Codex/controller from applying implementation fixes",
        )

    def test_no_advance_after_non_approved_verdict(self) -> None:
        patterns = (
            r"not.*advance.*fix-required",
            r"not.*advance.*blocked",
            r"no.*ledger.*fix-required",
            r"no.*ledger.*blocked",
            r"not.*mark.*complete.*fix-required",
            r"not.*background smoke",
            r"no.*advance.*non-approved",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must forbid advance, ledger completion, or background smoke after non-approved verdict",
        )

    def test_references_bridge_and_execution_skills(self) -> None:
        self.assertIn("cursor-agent-bridge", self.combined)
        self.assertIn("executing-plans-with-cursor", self.combined)
        reference_patterns = (
            r"reference",
            r"read the",
            r"do not copy",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in reference_patterns),
            "Skill must reference bridge/execution skills without copying procedures",
        )

    def test_pressure_resistance_deadline_never_exception(self) -> None:
        self.assertIn("deadline", self.combined)
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in NEVER_EXCEPTION_PATTERNS),
            "Skill must state deadline pressure is never an exception",
        )

    def test_pressure_resistance_trust_report_never_exception(self) -> None:
        trust_patterns = (
            r"trust.*report",
            r"never trust",
            r"not trust.*report",
            r"report alone",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in trust_patterns),
            "Skill must resist trusting the worker report alone",
        )

    def test_required_body_sections_present(self) -> None:
        for section in REVIEW_REQUIRED_BODY_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, self.combined)

    def test_no_todo_placeholders_remain(self) -> None:
        self.assertNotRegex(self.body, r"\[TODO", msg="SKILL.md still contains TODO placeholders")


if __name__ == "__main__":
    unittest.main()
