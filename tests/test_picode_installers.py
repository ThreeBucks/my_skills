from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install-picode.sh"
UNINSTALL = ROOT / "uninstall-picode.sh"
MARKER = ".my-skills-install.json"


def run_script(script: Path, tmp: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(script),
            "--picode-home",
            str(tmp / "picode"),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


class PicodeInstallerTests(unittest.TestCase):
    def test_install_and_uninstall_round_trip_managed_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            install = run_script(INSTALL, tmp)

            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            skills = tmp / "picode" / "skills"
            self.assertTrue((skills / "dev-baseline" / MARKER).is_file())
            self.assertTrue((skills / "rtk" / MARKER).is_file())
            self.assertTrue((skills / "diagnose" / "SKILL.md").is_file())
            self.assertTrue((skills / "test-driven-development" / "SKILL.md").is_file())
            picode_md = (tmp / "picode" / "picode.md").read_text(encoding="utf-8")
            self.assertIn("my_skills:picode-default-skills:start", picode_md)
            self.assertIn("- dev-baseline", picode_md)
            self.assertIn("- karpathy-guidelines", picode_md)
            self.assertIn("- rtk", picode_md)

            uninstall = run_script(UNINSTALL, tmp)

            self.assertEqual(uninstall.returncode, 0, uninstall.stdout + uninstall.stderr)
            self.assertFalse((skills / "dev-baseline").exists())
            self.assertFalse((skills / "diagnose").exists())
            self.assertNotIn(
                "my_skills:picode-default-skills:start",
                (tmp / "picode" / "picode.md").read_text(encoding="utf-8"),
            )

    def test_install_refuses_unmarked_existing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            foreign = tmp / "picode" / "skills" / "dev-baseline"
            foreign.mkdir(parents=True)
            sentinel = foreign / "SENTINEL"
            sentinel.write_text("foreign", encoding="utf-8")

            result = run_script(INSTALL, tmp)

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "foreign")

    def test_force_install_takes_ownership_of_unmarked_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            foreign = tmp / "picode" / "skills" / "dev-baseline"
            foreign.mkdir(parents=True)
            (foreign / "SENTINEL").write_text("foreign", encoding="utf-8")

            result = run_script(INSTALL, tmp, "--force")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((foreign / "SENTINEL").exists())
            self.assertTrue((foreign / MARKER).is_file())

    def test_uninstall_skips_unmanaged_skill_and_preserves_user_picode_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            skill = tmp / "picode" / "skills" / "dev-baseline"
            skill.mkdir(parents=True)
            picode_md = tmp / "picode" / "picode.md"
            picode_md.write_text("user notes\n", encoding="utf-8")

            result = run_script(UNINSTALL, tmp)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(skill.exists())
            self.assertEqual(picode_md.read_text(encoding="utf-8"), "user notes\n")

    def test_install_default_block_only_adds_missing_default_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            picode_md = tmp / "picode" / "picode.md"
            picode_md.parent.mkdir(parents=True)
            picode_md.write_text(
                "每次新会话开始时，自动加载以下 skills：\n\n"
                "- dev-baseline\n"
                "- karpathy-guidelines\n",
                encoding="utf-8",
            )

            result = run_script(INSTALL, tmp)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            content = picode_md.read_text(encoding="utf-8")
            self.assertEqual(content.count("- dev-baseline"), 1)
            self.assertEqual(content.count("- karpathy-guidelines"), 1)
            self.assertIn("- rtk", content)


if __name__ == "__main__":
    unittest.main()
