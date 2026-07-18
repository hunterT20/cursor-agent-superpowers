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
    "Use when a user wants a controller to plan, review, or verify work while Cursor Agent "
    "performs every semantic implementation and semantic review-fix edit and the controller may "
    "apply only verified mechanical review patches. Upstream Superpowers is optional; "
    "when available, ask once per task before routing through upstream workflows."
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

    def test_description_states_semantic_edits_and_mechanical_exception(self) -> None:
        desc = self.frontmatter["description"].lower()
        self.assertIn("semantic", desc)
        self.assertIn("mechanical", desc)
        self.assertNotIn(
            "every implementation and review-fix edit",
            desc,
            "Description must not regress to blanket every review-fix edit wording",
        )

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

    def test_semantic_review_fixes_route_to_cursor(self) -> None:
        patterns = (
            r"review-fix",
            r"review fix",
            r"fix edits",
        )
        self.assertTrue(
            any(term in self.combined for term in patterns),
            "Skill must mention review-fix edits",
        )
        route_patterns = (
            r"review-fix.*cursor",
            r"cursor.*review-fix",
            r"semantic.*review-fix.*cursor",
            r"semantic.*fix.*cursor agent",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in route_patterns),
            "Skill must route semantic review-fix edits to Cursor Agent",
        )

    def test_mechanical_patch_exception_is_semantics_based(self) -> None:
        mechanical_patterns = (
            r"mechanical",
            r"mechanical.*patch",
            r"mechanical.*review",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in mechanical_patterns),
            "Skill must define a mechanical review-patch exception",
        )
        semantic_patterns = (
            r"semantic",
            r"non-semantic",
            r"deterministic",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in semantic_patterns),
            "Skill must base the exception on edit semantics, not severity",
        )

    def test_mechanical_patch_allowlist_exhaustive(self) -> None:
        allowlist_terms = (
            "formatter",
            "whitespace",
            "typo",
            "non-executable prose",
            "comment",
        )
        for term in allowlist_terms:
            with self.subTest(term=term):
                self.assertIn(term, self.combined, f"Mechanical allowlist must include {term!r}")

    def test_mechanical_patch_denylist_exhaustive(self) -> None:
        denylist_terms = (
            "executable code",
            "test",
            "configuration",
            "schema",
            "dependenc",
            "lockfile",
            "generated output",
            "public api",
            "security",
            "authentication",
            "business logic",
            "code block",
        )
        for term in denylist_terms:
            with self.subTest(term=term):
                self.assertIn(term, self.combined, f"Mechanical denylist must include {term!r}")

    def test_minor_severity_alone_not_mechanical_patch_authorization(self) -> None:
        patterns = (
            r"minor.*not.*(enough|sufficient|alone|authorize)",
            r"minor.*severity.*not",
            r"not.*minor.*alone",
            r"severity.*not.*authorize",
            r"line count.*not",
            r"small.*line.*not",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must state minor severity or line count alone never authorizes a controller patch",
        )

    def test_mechanical_patch_allowed_files_and_no_scope_expansion(self) -> None:
        scope_patterns = (
            r"allowed files",
            r"active.*brief",
            r"no scope expansion",
            r"does not expand scope",
            r"unambiguous ownership",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in scope_patterns),
            "Skill must limit mechanical patches to allowed brief files with no scope expansion",
        )

    def test_mechanical_patch_evidence_and_rereview_required(self) -> None:
        evidence_patterns = (
            r"controller-patch",
            r"controller patch",
            r"patch evidence",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in evidence_patterns),
            "Skill must require durable controller-patch evidence",
        )
        for field in ("finding", "classification", "controller identity", "verification"):
            with self.subTest(field=field):
                self.assertIn(field, self.combined, f"Patch evidence must include {field!r}")
        rereview_patterns = (
            r"re-review.*before.*approv",
            r"rerun.*covering",
            r"exact.*covering.*verification",
            r"covering verification.*rerun",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in rereview_patterns),
            "Skill must require exact covering verification rerun and re-review before approval",
        )

    def test_mechanical_patch_fallback_to_cursor_on_ambiguity(self) -> None:
        fallback_patterns = (
            r"uncertain.*cursor-agent-bridge",
            r"ambiguous.*cursor-agent-bridge",
            r"uncertain.*consolidated fix brief",
            r"verification fail.*cursor-agent-bridge",
            r"scope expand.*cursor-agent-bridge",
            r"patch grow.*cursor-agent-bridge",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in fallback_patterns),
            "Skill must route ambiguous, growing, or failed mechanical patches to Cursor",
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

    def test_detects_upstream_superpowers_availability_at_task_start(self) -> None:
        patterns = (
            r"check.*whether.*upstream.*superpowers.*available",
            r"at.*task start.*check.*upstream",
            r"upstream.*superpowers.*available.*runtime",
            r"whether upstream.*superpowers.*skills.*available",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must check upstream Superpowers availability at task start",
        )

    def test_native_fallback_when_upstream_unavailable(self) -> None:
        required_capabilities = (
            ("planning", r"controller-native.*planning"),
            ("review", r"controller-native.*review"),
            ("verification", r"controller-native.*verification"),
            ("branch completion", r"controller-native.*branch"),
        )
        for capability, pattern in required_capabilities:
            with self.subTest(capability=capability):
                self.assertTrue(
                    re.search(pattern, self.combined, re.DOTALL),
                    f"Skill must use controller-native {capability} when unavailable",
                )
        non_block_patterns = (
            r"do not block",
            r"not a blocker",
            r"not block",
            r"must not.*block",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in non_block_patterns),
            "Skill must not block when upstream Superpowers is unavailable",
        )
        install_patterns = (
            r"do not.*must be installed",
            r"not.*must be installed",
            r"not.*insist.*install",
            r"do not.*insist.*install",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in install_patterns),
            "Skill must not insist upstream Superpowers must be installed",
        )

    def test_once_per_task_confirmation_when_available(self) -> None:
        patterns = (
            r"ask.*once.*whole task",
            r"once per task",
            r"once for the whole task",
            r"one.*confirmation.*task",
            r"ask the user once",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must ask once per task when upstream Superpowers is available",
        )

    def test_no_upstream_task_routing_before_confirmation(self) -> None:
        patterns = (
            r"do not invoke.*upstream.*before.*confirm",
            r"not route.*upstream.*before.*confirm",
            r"do not.*route.*task through upstream",
            r"before.*affirmative confirmation",
            r"until the user confirms",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must not route through upstream Superpowers workflows before user confirmation",
        )

    def test_honors_confirmed_upstream_or_native_choice(self) -> None:
        honor_patterns = (
            r"honor.*explicit.*choice",
            r"honor.*user.*choice",
            r"explicit user choice",
            r"governs the entire task",
            r"whole task.*unless the user changes",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in honor_patterns),
            "Skill must honor confirmed upstream or native choice for the whole task",
        )
        route_patterns = (
            r"if.*confirm.*upstream",
            r"if.*declin.*controller-native",
            r"if the user confirms",
            r"if the user declines",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in route_patterns),
            "Skill must branch on confirmed upstream use or confirmed native handling",
        )

    def test_preserves_mandatory_overlay_routing_in_both_routes(self) -> None:
        both_route_patterns = (
            r"both routes",
            r"in both routes",
            r"either route",
            r"whether.*unavailable.*available",
            r"unavailable or declined",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in both_route_patterns),
            "Skill must state overlay routing applies in both upstream and native routes",
        )
        for skill in REQUIRED_OVERLAY_SKILLS:
            with self.subTest(skill=skill):
                self.assertIn(skill, self.combined)


EXECUTING_PLANS_WITH_CURSOR = REPO_ROOT / "skills" / "executing-plans-with-cursor" / "SKILL.md"
EXECUTION_CONTRACTS_REFERENCE = (
    REPO_ROOT / "skills" / "executing-plans-with-cursor" / "references" / "execution-contracts.md"
)

EXECUTION_EXPECTED_NAME = "executing-plans-with-cursor"
EXECUTION_EXPECTED_DESCRIPTION = (
    "Use when an approved implementation plan must be executed task-by-task by "
    "Cursor Agent, defaulting to sequential dispatch in one worktree and allowing "
    "parallel isolated waves only when dependency and integration-surface proof is explicit."
)
EXECUTION_OPENAI_YAML = (
    REPO_ROOT / "skills" / "executing-plans-with-cursor" / "agents" / "openai.yaml"
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

    def test_sequential_is_default_path(self) -> None:
        default_patterns = (
            r"sequential.*default",
            r"default.*sequential",
            r"sequential.*safe default",
            r"default.*one\s+shared\s+worktree",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in default_patterns),
            "Skill must document sequential execution as the safe default",
        )
        shared_patterns = (
            r"shared\s+worktree",
            r"one\s+worktree",
            r"same\s+worktree",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in shared_patterns),
            "Sequential path must use one shared worktree",
        )

    def test_sequential_plan_does_not_require_parallel_only_proof(self) -> None:
        prereq_section = re.search(
            r"## prerequisites.*?(?=## |\Z)",
            self.combined,
            re.DOTALL,
        )
        self.assertIsNotNone(prereq_section, "Skill must define prerequisites")
        prereq_text = prereq_section.group(0)
        parallel_only_patterns = (
            r"dependency\s+graph.*only.*parallel",
            r"parallel.*only.*dependency\s+graph",
            r"write.?set.*only.*parallel",
            r"parallel.*only.*write.?set",
            r"only\s+when.*parallel.*dependency\s+graph",
        )
        self.assertTrue(
            any(re.search(pattern, prereq_text, re.DOTALL) for pattern in parallel_only_patterns)
            or (
                "dependency graph" not in prereq_text.split("routing decision")[0]
                and "write set" not in prereq_text.split("routing decision")[0]
            ),
            "Universal prerequisites must not require dependency graph or write sets for sequential plans",
        )
        parallel_gate_patterns = (
            r"parallel.*dependency\s+graph",
            r"authorize.*parallel.*dependency\s+graph",
            r"parallel.*write.?set",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in parallel_gate_patterns),
            "Parallel authorization must still require dependency graph and write-set declarations",
        )

    def test_integration_requires_all_tasks_approved_isolated(self) -> None:
        self.assertNotRegex(
            self.full_combined,
            r"approved-isolated.*\bor\b.*blocked",
            "Integration must not start when any wave task is blocked",
        )
        all_approved_patterns = (
            r"every\s+wave\s+task.*approved-isolated",
            r"all\s+wave\s+tasks.*approved-isolated",
            r"only\s+when\s+every.*approved-isolated",
            r"every\s+task.*approved-isolated.*before.*integrat",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in all_approved_patterns),
            "Integration may start only when every wave task is approved-isolated",
        )
        subset_patterns = (
            r"do\s+not.*integrat.*subset",
            r"not.*subset.*integrat",
            r"prevent.*integrat.*not-yet-integrated",
            r"do\s+not\s+integrate\s+a\s+subset",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in subset_patterns),
            "Skill must forbid integrating a subset when other wave tasks failed or blocked",
        )

    def test_mid_integration_failure_preserves_history_without_rollback(self) -> None:
        pre_integration_patterns = (
            r"every\s+wave\s+task.*approved-isolated.*before.*integrat",
            r"only\s+when\s+every.*approved-isolated",
            r"do\s+not\s+integrate\s+a\s+subset",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in pre_integration_patterns),
            "Pre-integration rule must require every task approved-isolated before integration begins",
        )
        mid_failure_patterns = (
            r"preserve.*already-integrated\s+head",
            r"already-integrated\s+head.*preserve",
            r"stop.*before.*integrat.*remaining",
            r"not-yet-integrated\s+branch",
            r"do\s+not\s+reset.*history",
            r"not\s+reset.*rewrite.*rollback",
            r"auto-rollback",
            r"recovery\s+decision",
            r"pre-wave\s+head",
        )
        matched = sum(
            1
            for pattern in mid_failure_patterns
            if re.search(pattern, self.full_combined, re.DOTALL)
        )
        self.assertGreaterEqual(
            matched,
            4,
            "Mid-integration failures must preserve integrated HEADs, stop remaining merges, forbid rollback, and require recovery",
        )
        self.assertNotRegex(
            self.full_combined,
            r"\*\*no\s+partial\s+integration\.?\*\*",
            "Absolute 'no partial integration' must be qualified for mid-integration failure cases",
        )

    def test_task_worktree_execution_artifacts_not_worker_only(self) -> None:
        self.assertNotRegex(
            self.full_combined,
            r"worker\s+artifacts?\s+only",
            "Task worktree artifacts must not be described as worker-only",
        )
        model_patterns = (
            r"task-scoped\s+execution\s+artifact",
            r"task-scoped\s+execution\s+evidence",
            r"execution\s+artifacts?/evidence",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in model_patterns),
            "Task worktree section must use task-scoped execution artifacts/evidence wording",
        )
        controller_artifacts = ("brief.md", "review-brief.md", "controller-patch.md")
        worker_artifacts = ("report.md", "run-record", "stdout", "stderr")
        for artifact in controller_artifacts + worker_artifacts:
            with self.subTest(artifact=artifact):
                self.assertIn(artifact.replace("-", " "), self.full_combined.replace("-", " "))
        authority_patterns = (
            r"integration\s+ledger.*sole.*source",
            r"not.*alternate.*state.*authorit",
            r"evidence.*not.*alternate.*authorit",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in authority_patterns),
            "Task-scoped execution artifacts must remain evidence with integration ledger as sole state authority",
        )

    def test_integration_ledger_is_sole_authority(self) -> None:
        authority_patterns = (
            r"authoritative.*integration.*ledger",
            r"integration.*ledger.*sole.*source",
            r"sole\s+source.*integration.*ledger",
            r"authoritative.*progress\.md",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in authority_patterns),
            "Integration worktree progress.md must be the sole authoritative ledger",
        )
        worker_not_authority_patterns = (
            r"worker.*not.*alternate.*authorit",
            r"not.*alternate.*state.*authorit",
            r"evidence.*not.*alternate.*authorit",
            r"local\s+artifacts.*evidence",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in worker_not_authority_patterns),
            "Worker reports and local artifacts must be evidence, not alternate state authorities",
        )
        resume_patterns = (
            r"resume.*integration\s+ledger",
            r"integration\s+ledger.*resume",
            r"resume.*authoritative.*ledger",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in resume_patterns),
            "Resume must start from the authoritative integration ledger",
        )

    def test_integration_ledger_records_worktree_and_sha_fields(self) -> None:
        ledger_fields = (
            "worktree path",
            "artifact root",
            "task commit",
            "integrated head",
            "wave-base head",
        )
        for field in ledger_fields:
            with self.subTest(field=field):
                self.assertIn(field.replace("-", " "), self.full_combined.replace("-", " "))
        wave_evidence_patterns = (
            r"wave.*evidence.*integration\s+worktree",
            r"integration\s+worktree.*wave.*evidence",
            r"wave-<id>/evidence\.md",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in wave_evidence_patterns),
            "Wave evidence must live in the integration worktree",
        )

    def test_bridge_head_invariant_separate_from_controller_commits(self) -> None:
        bridge_patterns = (
            r"bridge.*head\s+invariant",
            r"head\s+invariant.*every\s+cursor",
            r"head\s+invariant.*bridge",
            r"every\s+cursor\s+invocation.*head",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in bridge_patterns),
            "Bridge HEAD invariant must apply across every Cursor invocation",
        )
        controller_commit_patterns = (
            r"approved-isolated.*controller.*commit",
            r"controller.*task\s+commit",
            r"record.*task\s+commit.*sha",
            r"task\s+commit\s+sha",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in controller_commit_patterns),
            "Controller task commits after approved-isolated must be recorded separately from worker HEAD",
        )
        unrecorded_patterns = (
            r"unrecorded.*head.*blocker",
            r"unrecorded.*head.*stop",
            r"unrecorded.*head.*remain",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in unrecorded_patterns),
            "Unrecorded HEAD changes must remain blockers",
        )

    def test_integration_and_sibling_task_worktrees(self) -> None:
        self.assertIn("integration worktree", self.full_combined)
        sibling_patterns = (
            r"sibling.*worktree",
            r"task\s+worktree.*sibling",
            r"never\s+nested",
            r"not\s+nested",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in sibling_patterns),
            "Task worktrees must be sibling isolated worktrees, never nested",
        )
        creation_patterns = (
            r"platform-native.*worktree",
            r"primary.*checkout",
            r"common\s+checkout",
            r"not.*recursively.*inside.*linked\s+worktree",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in creation_patterns),
            "Sibling task worktrees must be created from the primary checkout, not recursively inside a linked worktree",
        )
        record_patterns = (
            r"record.*worktree\s+path.*integration\s+ledger",
            r"integration\s+ledger.*worktree\s+path",
            r"absolute.*worktree\s+path",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in record_patterns),
            "Every task worktree path must be recorded in the integration ledger",
        )

    def test_ambiguous_independence_routes_to_sequential(self) -> None:
        patterns = (
            r"ambiguous.*sequential",
            r"incomplete.*sequential",
            r"missing.*sequential",
            r"proof.*missing.*sequential",
            r"when.*proof.*missing.*sequential",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in patterns),
            "Skill must require sequential execution when independence proof is missing or ambiguous",
        )

    def test_parallel_wave_requires_dependency_graph_without_edges(self) -> None:
        graph_patterns = (
            r"dependency\s+graph",
            r"no\s+direct.*transitive.*depend",
            r"no\s+dependency\s+edge",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in graph_patterns),
            "Parallel wave must require an explicit dependency graph with no edges among wave tasks",
        )

    def test_parallel_wave_requires_disjoint_write_sets(self) -> None:
        patterns = (
            r"disjoint.*write\s+set",
            r"write\s+set.*disjoint",
            r"intended\s+write\s+set",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in patterns),
            "Parallel wave must require declared disjoint write sets",
        )

    def test_parallel_wave_requires_no_shared_integration_surfaces(self) -> None:
        surface_terms = (
            "api",
            "schema",
            "configuration",
            "lockfile",
            "generated output",
            "migration",
        )
        for term in surface_terms:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    self.full_combined,
                    f"Parallel wave gate must cover shared integration surface {term!r}",
                )
        integration_patterns = (
            r"integration-sensitive",
            r"shared.*contract",
            r"no\s+shared",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in integration_patterns),
            "Parallel wave must forbid shared integration-sensitive contracts",
        )

    def test_file_disjointness_and_independent_label_insufficient(self) -> None:
        insufficient_patterns = (
            r"file\s+disjoint.*insufficient",
            r"disjoint.*alone.*insufficient",
            r"independent.*label.*insufficient",
            r"independent.*alone.*insufficient",
            r"label.*alone.*insufficient",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in insufficient_patterns),
            "Skill must state file disjointness or an independent label alone is insufficient",
        )

    def test_parallel_wave_concurrency_cap_three(self) -> None:
        cap_patterns = (
            r"(?:cap|maximum|at most|no more than).*(?:three|3).*(?:concurrent|parallel|active)",
            r"(?:three|3).*(?:concurrent|parallel|active).*(?:cursor\s+)?task",
            r"concurrency.*(?:three|3)",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in cap_patterns),
            "Parallel wave must cap concurrently active Cursor tasks at three",
        )

    def test_parallel_wave_per_task_isolation(self) -> None:
        isolation_terms = (
            ("branch", r"\bbranch\b"),
            ("worktree", r"worktree"),
            ("session", r"fresh\s+cursor\s+session|one\s+fresh\s+cursor\s+session"),
            ("artifact root", r"artifact\s+root|task-scoped\s+artifact"),
            ("progress entry", r"progress\s+entry|progress\.md"),
            ("brief", r"brief\.md"),
            ("report", r"report\.md"),
            ("run record", r"run-record"),
            ("stdout", r"stdout"),
            ("stderr", r"stderr"),
            ("review", r"reviewing-cursor-changes|review\s+gate"),
            ("head invariant", r"head\s+invariant|head"),
        )
        for label, pattern in isolation_terms:
            with self.subTest(isolation=label):
                self.assertTrue(
                    re.search(pattern, self.full_combined, re.DOTALL),
                    f"Parallel wave must give each task its own {label}",
                )

    def test_parallel_wave_shared_wave_base_head(self) -> None:
        patterns = (
            r"wave-base.*head",
            r"same.*recorded.*integration\s+head",
            r"start.*same.*integration\s+head",
            r"wave.*same.*head",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in patterns),
            "All branches in one wave must start from the same recorded wave-base integration HEAD",
        )
        later_wave_patterns = (
            r"later\s+wave.*updated\s+integration\s+head",
            r"updated\s+integration\s+head.*later\s+wave",
            r"next\s+wave.*updated\s+integration",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in later_wave_patterns),
            "Later waves must start from the updated integration HEAD",
        )

    def test_worker_git_operations_remain_prohibited_in_parallel_waves(self) -> None:
        git_terms = ("commit", "push", "merge", "rebase", "reset", "tag", "branch switch", "worktree")
        for term in git_terms:
            with self.subTest(git_action=term):
                self.assertIn(term, self.full_combined, f"Parallel path must prohibit Cursor {term}")

    def test_approved_isolated_before_integration(self) -> None:
        self.assertIn("approved-isolated", self.full_combined)
        not_final_patterns = (
            r"approved-isolated.*not.*(?:complete|final|approved)",
            r"not.*(?:complete|final\s+completion|approved).*(?:until|before).*integrat",
            r"approved-isolated.*before.*integrat",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in not_final_patterns),
            "Isolated review must yield approved-isolated, not final approved, before integration",
        )

    def test_controller_owned_integration_after_parallel_wave(self) -> None:
        controller_patterns = (
            r"controller.*commit",
            r"controller-owned.*commit",
            r"controller\s+commits",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in controller_patterns),
            "Controller must commit approved task branches after isolated review",
        )
        integration_patterns = (
            r"integrat.*one\s+at\s+a\s+time",
            r"sequential\s+integrat",
            r"plan\s+order",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in integration_patterns),
            "Controller must integrate branches sequentially in declared plan order",
        )
        verification_patterns = (
            r"affected.*verif.*after.*integrat",
            r"after\s+every\s+integrat.*verif",
            r"full.*suite.*wave\s+end",
            r"full.*required\s+suite.*wave",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in verification_patterns),
            "Controller must rerun affected verification after each integration and full suite at wave end",
        )
        approved_after_patterns = (
            r"only\s+then.*approved",
            r"then.*mark.*approved",
            r"approved.*after.*integrat",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in approved_after_patterns),
            "Tasks become approved only after integration and verification complete",
        )

    def test_parallel_wave_stop_and_sequential_fallback(self) -> None:
        stop_terms = (
            "overlap",
            "merge conflict",
            "integration-test failure",
            "integration test failure",
        )
        for term in stop_terms:
            with self.subTest(stopper=term):
                self.assertIn(term.replace("-", " ").replace("  ", " "), self.full_combined.replace("-", " "))
        head_patterns = (
            r"unexpected\s+head",
            r"head.*chang.*stop",
            r"head\s+mutation",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in head_patterns),
            "Unexpected HEAD change must stop the wave",
        )
        fallback_patterns = (
            r"do\s+not\s+automatically\s+merge",
            r"not\s+automatically\s+merge",
            r"fall\s+back.*sequential",
            r"fresh\s+sequential\s+path",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in fallback_patterns),
            "Wave blockers must stop auto-merge and fall back to sequential execution",
        )

    def test_parallel_wave_preserves_bridge_review_and_mechanical_patch(self) -> None:
        self.assertIn("cursor-agent-bridge", self.full_combined)
        self.assertIn("reviewing-cursor-changes", self.full_combined)
        mechanical_patterns = (
            r"mechanical",
            r"mechanical.*patch",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in mechanical_patterns),
            "Parallel path must preserve the mechanical controller-patch exception",
        )

    def test_openai_default_prompt_allows_guarded_parallel_route(self) -> None:
        self.assertTrue(EXECUTION_OPENAI_YAML.is_file(), "agents/openai.yaml must exist")
        prompt = EXECUTION_OPENAI_YAML.read_text(encoding="utf-8").lower()
        self.assertNotIn("always sequential", prompt)
        self.assertNotIn("one worktree only", prompt)
        guarded_patterns = (
            r"sequential.*default",
            r"default.*sequential",
            r"parallel.*only.*proof",
            r"dependency.*proof",
        )
        self.assertTrue(
            any(re.search(pattern, prompt, re.DOTALL) for pattern in guarded_patterns),
            "UI default prompt must not force always-sequential execution",
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

    def test_mechanical_review_patch_exception_in_execution_skill(self) -> None:
        mechanical_patterns = (
            r"mechanical",
            r"mechanical.*patch",
            r"mechanical.*review",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in mechanical_patterns),
            "Execution skill must document the mechanical review-patch exception",
        )
        semantic_patterns = (
            r"semantic.*review-fix",
            r"review-fix.*semantic",
            r"semantic.*implementation",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in semantic_patterns),
            "Execution skill must preserve Cursor ownership of semantic review-fix edits",
        )
        blanket_patterns = (
            r"every implementation and review-fix edit belongs to cursor",
            r"every implementation and review-fix edit belongs to cursor agent",
        )
        self.assertFalse(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in blanket_patterns),
            "Execution skill must not claim all review-fix edits are Cursor-only without the mechanical exception",
        )
        reference_patterns = (
            r"reviewing-cursor-changes",
            r"execution-contracts",
        )
        for pattern in reference_patterns:
            with self.subTest(pattern=pattern):
                self.assertIn(
                    pattern,
                    self.full_combined,
                    f"Mechanical exception must reference {pattern!r}",
                )

    def test_required_body_sections_present(self) -> None:
        for section in EXECUTION_REQUIRED_BODY_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, self.combined)

    def test_combined_reference_body_sections_present(self) -> None:
        for section in EXECUTION_COMBINED_BODY_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, self.full_combined)

    def test_pressure_resistance_parallel_without_proof_never_exception(self) -> None:
        parallel_patterns = (
            r"parallel",
            r"fan-out",
            r"fan out",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in parallel_patterns),
            "Skill must address parallel-worker pressure",
        )
        proof_patterns = (
            r"without.*proof.*sequential",
            r"proof.*missing.*sequential",
            r"never.*parallel.*without",
            r"not.*parallel.*without.*proof",
            r"pressure.*not.*bypass",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in proof_patterns),
            "Skill must refuse parallel pressure that bypasses dependency and integration proof",
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


def load_review_skill() -> tuple[dict[str, str], str, str, str, str]:
    text = REVIEWING_CURSOR_CHANGES.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    combined = f"{frontmatter.get('description', '')}\n{body}".lower()
    reference = ""
    if EXECUTION_CONTRACTS_REFERENCE.is_file():
        reference = EXECUTION_CONTRACTS_REFERENCE.read_text(encoding="utf-8")
    full_combined = f"{combined}\n{reference}".lower()
    return frontmatter, body, combined, reference, full_combined


class ReviewingCursorChangesContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frontmatter, cls.body, cls.combined, cls.reference, cls.full_combined = (
            load_review_skill()
        )

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

    def test_semantic_fixes_remain_cursor_only(self) -> None:
        patterns = (
            r"controller.*must not.*edit",
            r"codex.*must not.*edit",
            r"must not.*implementation fix",
            r"does not edit.*implementation",
            r"cursor owns.*fix",
        )
        self.assertTrue(
            any(re.search(pattern, self.combined, re.DOTALL) for pattern in patterns),
            "Skill must forbid Codex/controller from applying semantic implementation fixes",
        )

    def test_mechanical_review_patch_exception_defined(self) -> None:
        mechanical_patterns = (
            r"mechanical",
            r"mechanical.*patch",
            r"mechanical.*review",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in mechanical_patterns),
            "Review contract must define a mechanical review-patch exception",
        )

    def test_mechanical_patch_allowlist_in_review_contract(self) -> None:
        allowlist_terms = (
            "formatter",
            "whitespace",
            "typo",
            "non-executable prose",
            "comment",
        )
        for term in allowlist_terms:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    self.full_combined,
                    f"Review mechanical allowlist must include {term!r}",
                )

    def test_mechanical_patch_denylist_in_review_contract(self) -> None:
        denylist_terms = (
            "executable code",
            "test",
            "configuration",
            "schema",
            "dependenc",
            "lockfile",
            "generated output",
            "public api",
            "security",
            "authentication",
            "business logic",
            "code block",
        )
        for term in denylist_terms:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    self.full_combined,
                    f"Review mechanical denylist must include {term!r}",
                )

    def test_minor_severity_not_sufficient_for_controller_patch(self) -> None:
        patterns = (
            r"minor.*not.*(enough|sufficient|alone|authorize)",
            r"minor.*severity.*not",
            r"not.*minor.*alone",
            r"severity.*not.*authorize",
            r"line count.*not",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in patterns),
            "Review contract must state minor severity alone never authorizes a controller patch",
        )

    def test_task_remains_in_review_during_controller_patch(self) -> None:
        patterns = (
            r"in-review.*controller patch",
            r"controller patch.*in-review",
            r"remains.*in-review",
            r"stay.*in-review",
            r"in-review.*mechanical",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in patterns),
            "Task must remain in-review while a controller mechanical patch is applied",
        )

    def test_controller_patch_evidence_artifact_required(self) -> None:
        self.assertIn("controller-patch", self.full_combined)
        for field in ("finding", "classification", "controller identity", "verification"):
            with self.subTest(field=field):
                self.assertIn(
                    field,
                    self.full_combined,
                    f"Controller-patch evidence must record {field!r}",
                )

    def test_mechanical_patch_requires_exact_rerun_and_rereview(self) -> None:
        rerun_patterns = (
            r"exact.*covering",
            r"covering verification",
            r"rerun.*verification",
            r"rerun.*covering",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in rerun_patterns),
            "Mechanical patch must require exact covering verification rerun",
        )
        self.assertTrue(
            re.search(r"re-review.*before.*approv", self.full_combined, re.DOTALL)
            or "re-review" in self.full_combined and "approved" in self.full_combined,
            "Mechanical patch must require fresh diff re-review before approved",
        )

    def test_mechanical_patch_fallback_to_cursor_bridge(self) -> None:
        fallback_patterns = (
            r"uncertain.*cursor-agent-bridge",
            r"ambiguous.*cursor-agent-bridge",
            r"uncertain.*consolidated fix brief",
            r"verification fail.*cursor-agent-bridge",
            r"scope expand.*cursor-agent-bridge",
            r"patch grow.*cursor-agent-bridge",
            r"consolidated fix brief.*cursor-agent-bridge",
        )
        self.assertTrue(
            any(re.search(pattern, self.full_combined, re.DOTALL) for pattern in fallback_patterns),
            "Uncertain, growing, or failed mechanical patches must route to Cursor via bridge",
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
