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


if __name__ == "__main__":
    unittest.main()
