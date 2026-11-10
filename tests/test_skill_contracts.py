"""Static distribution contracts; behavioral quality is evaluated separately."""
from __future__ import annotations

import runpy
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {
    "dev-baseline", "design-workflow", "execute-work", "systematic-debugging",
    "test-driven-development", "code-review-workflow", "doc-coauthoring",
    "verification-before-completion",
}


class SkillContractTests(unittest.TestCase):
    def test_exactly_eight_public_entries(self):
        entries = list((ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual({p.parent.name for p in entries}, NAMES)
        self.assertEqual(len(entries), 8)

    def test_no_legacy_discoverable_entries(self):
        extra = [str(p.relative_to(ROOT)) for p in ROOT.rglob("SKILL.md")
                 if "skills" not in p.relative_to(ROOT).parts[:1]]
        self.assertEqual(extra, [])

    def test_frontmatter_names_and_bounded_entry_size(self):
        for name in sorted(NAMES):
            with self.subTest(skill=name):
                text = (ROOT / "skills" / name / "SKILL.md").read_text()
                self.assertTrue(text.startswith("---\n"))
                self.assertIn(f"name: {name}\n", text)
                self.assertRegex(text, r"(?m)^description: .+")
                self.assertLess(len(text.splitlines()), 200)
                self.assertNotRegex(text, r"(?m)^(hooks|auto_bootstrap):")

    def test_all_local_markdown_links_resolve_inside_skill(self):
        for name in sorted(NAMES):
            home = ROOT / "skills" / name
            for page in home.rglob("*.md"):
                for href in re.findall(r"\]\(([^)\s]+)\)", page.read_text()):
                    if "://" in href or href.startswith("#"):
                        continue
                    target = (page.parent / href.split("#", 1)[0]).resolve()
                    with self.subTest(page=str(page), href=href):
                        self.assertTrue(target.is_relative_to(home.resolve()))
                        self.assertTrue(target.is_file(), str(target))

    def test_no_domain_routes_or_runtime_plugin_payload(self):
        for page in (ROOT / "skills").rglob("*.md"):
            self.assertNotRegex(page.read_text(), r"AdaDnn|AdaEP|adaep-debugging|adadnn-ccl-dev")
        extensions = list((ROOT / "skills").rglob("package.json"))
        self.assertEqual(extensions, [])

    def test_behavior_cases_have_inputs_and_observable_expectations(self):
        cases = runpy.run_path(str(ROOT / "tests" / "workflow_cases.py"))["CASES"]
        self.assertGreaterEqual(len(cases), 10)
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        for case in cases:
            self.assertTrue(case["prompt"])
            self.assertTrue(case["must"])
            self.assertTrue(case["must_not"])
            self.assertTrue(set(case["skills"]).issubset(NAMES))


if __name__ == "__main__":
    unittest.main()
