from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install-codex.sh"
UNINSTALL = ROOT / "uninstall-codex.sh"
MARKER = ".my-skills-install.json"


def run_script(script: Path, tmp: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(script),
            "--codex-home",
            str(tmp / "codex"),
            "--agents-home",
            str(tmp / "agents"),
            "--plugin-home",
            str(tmp / "plugins"),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def run_script_with_default_plugin_home(
    script: Path,
    tmp: Path,
    *extra: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env["HOME"] = str(tmp)
    if env:
        merged_env.update(env)
    return subprocess.run(
        [
            str(script),
            "--codex-home",
            str(tmp / "codex"),
            "--agents-home",
            str(tmp / "agents"),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=merged_env,
    )


class CodexInstallerSafetyTests(unittest.TestCase):
    def test_install_refuses_unmarked_existing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            foreign = tmp / "codex" / "skills" / "agent-skill-creator"
            foreign.mkdir(parents=True)
            sentinel = foreign / "SENTINEL"
            sentinel.write_text("foreign", encoding="utf-8")

            result = run_script(INSTALL, tmp, "--no-plugin-add")

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "foreign")

    def test_install_refuses_unmarked_existing_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            foreign = tmp / "plugins" / "ok-skills"
            foreign.mkdir(parents=True)
            sentinel = foreign / "SENTINEL"
            sentinel.write_text("foreign", encoding="utf-8")

            result = run_script(INSTALL, tmp, "--no-plugin-add")

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "foreign")

    def test_uninstall_skips_unmarked_existing_skill_and_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            skill = tmp / "codex" / "skills" / "agent-skill-creator"
            plugin = tmp / "plugins" / "ok-skills"
            skill.mkdir(parents=True)
            plugin.mkdir(parents=True)

            result = run_script(UNINSTALL, tmp, "--no-plugin-remove")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(skill.exists())
            self.assertTrue(plugin.exists())

    def test_force_install_takes_ownership_of_unmarked_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            foreign = tmp / "codex" / "skills" / "agent-skill-creator"
            foreign.mkdir(parents=True)
            (foreign / "SENTINEL").write_text("foreign", encoding="utf-8")

            result = run_script(INSTALL, tmp, "--no-plugin-add", "--force")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((foreign / "SENTINEL").exists())
            self.assertTrue((foreign / MARKER).is_file())

    def test_force_uninstall_removes_unmarked_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            skill = tmp / "codex" / "skills" / "agent-skill-creator"
            skill.mkdir(parents=True)

            result = run_script(UNINSTALL, tmp, "--no-plugin-remove", "--force")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(skill.exists())

    def test_uninstall_removes_plugin_registration_even_when_source_dir_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            calls = tmp / "codex-calls.log"
            fake_codex = bin_dir / "codex"
            fake_codex.write_text(
                f"""#!/usr/bin/env sh
printf '%s\\n' "$*" >> {calls}
if [ "$1" = "plugin" ] && [ "$2" = "remove" ]; then
  exit 0
fi
exit 1
""",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)

            result = run_script_with_default_plugin_home(
                UNINSTALL,
                tmp,
                env={"PATH": f"{bin_dir}:{os.environ['PATH']}"},
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            call_text = calls.read_text(encoding="utf-8")
            self.assertIn("plugin remove ok-skills@personal", call_text)
            self.assertIn("plugin remove superpowers@personal", call_text)

    def test_install_and_uninstall_round_trip_managed_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            install = run_script(INSTALL, tmp, "--no-plugin-add")
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            self.assertTrue((tmp / "codex" / "skills" / "agent-skill-creator" / MARKER).is_file())
            self.assertTrue((tmp / "plugins" / "ok-skills" / MARKER).is_file())

            uninstall = run_script(UNINSTALL, tmp, "--no-plugin-remove")
            self.assertEqual(uninstall.returncode, 0, uninstall.stdout + uninstall.stderr)
            self.assertFalse((tmp / "codex" / "skills" / "agent-skill-creator").exists())
            self.assertFalse((tmp / "plugins" / "ok-skills").exists())

    def test_install_fails_when_codex_add_does_not_register_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            fake_codex = bin_dir / "codex"
            fake_codex.write_text(
                """#!/usr/bin/env sh
if [ "$1" = "plugin" ] && [ "$2" = "add" ]; then
  exit 0
fi
if [ "$1" = "plugin" ] && [ "$2" = "list" ]; then
  printf '%s\\n' 'Marketplace `personal`'
  printf '%s\\n' 'Path: /tmp/personal/marketplace.json'
  printf '%s\\n' '  ok-skills@personal (not installed)'
  printf '%s\\n' '  superpowers@personal (not installed)'
  exit 0
fi
exit 1
""",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)

            result = run_script_with_default_plugin_home(
                INSTALL,
                tmp,
                "--force",
                env={"PATH": f"{bin_dir}:{os.environ['PATH']}"},
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("not reported as installed", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
