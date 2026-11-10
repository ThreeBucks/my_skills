from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = '.my-skills-install.json'
NAMES = {'dev-baseline', 'design-workflow', 'execute-work', 'systematic-debugging',
         'test-driven-development', 'code-review-workflow', 'doc-coauthoring',
         'verification-before-completion'}
START = '<!-- my_skills:picode-default-skills:start -->'
END = '<!-- my_skills:picode-default-skills:end -->'


class InstallerContract:
    platform = 'picode'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name).resolve()
        self.repo = self.tmp / 'repo'
        shutil.copytree(ROOT / 'scripts', self.repo / 'scripts')
        for action in ['install', 'uninstall']:
            for platform in ['picode', 'codex']:
                shutil.copy2(ROOT / f'{action}-{platform}.sh', self.repo)
        for name in NAMES:
            path = self.repo / 'skills' / name
            path.mkdir(parents=True)
            (path / 'SKILL.md').write_text(f'---\nname: {name}\n---\n{name}\n')
            (path / 'assets').mkdir()
            (path / 'assets' / 'data.txt').write_text('asset')
        # Sources outside skills/ are never discoverable, even before migration.
        for path in [self.repo / 'rtk', self.repo / 'legacy' / 'old',
                     self.repo / 'superpowers' / 'skills' / 'old']:
            path.mkdir(parents=True)
            (path / 'SKILL.md').write_text('old')
        self.home = self.tmp / self.platform
        self.skills = self.home / 'skills'
        self.config = self.home / 'picode.md'

    def run_cli(self, *args, uninstall=False):
        env = os.environ.copy()
        env.update(HOME=str(self.tmp), PYTHONDONTWRITEBYTECODE='1')
        command = [str(self.repo /
                   f'{"uninstall" if uninstall else "install"}-{self.platform}.sh'),
                   f'--{self.platform}-home', str(self.home)]
        return subprocess.run(command + list(args), text=True, capture_output=True, env=env)

    def ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def rejected(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def legacy(self, name='rtk'):
        target = self.skills / name
        target.mkdir(parents=True, exist_ok=True)
        (target / 'SKILL.md').write_text('old')
        (target / MARKER).write_text(json.dumps({
            'installed_by': f'my_skills/install-{self.platform}.sh',
            'source_repo': str(self.repo), 'source_name': name,
            'kind': 'picode-skill' if self.platform == 'picode' else 'skill'}))
        return target

    def snapshot(self):
        if not self.home.exists():
            return {}
        return {str(p.relative_to(self.home)): p.read_bytes()
                for p in self.home.rglob('*') if p.is_file()}

    def test_eight_entries_round_trip(self):
        self.ok(self.run_cli())
        self.assertEqual({p.name for p in self.skills.iterdir()}, NAMES)
        marker = json.loads((self.skills / 'dev-baseline' / MARKER).read_text())
        self.assertEqual(marker['manifest_version'], 2)
        self.assertEqual(set(marker['manifest']), {'.', 'SKILL.md', 'assets/', 'assets/data.txt'})
        self.assertEqual(len(marker["manifest"]["SKILL.md"]["sha256"]), 64)
        self.ok(self.run_cli(uninstall=True))
        self.assertEqual(list(self.skills.iterdir()), [])

    def test_selection_and_exclude(self):
        self.ok(self.run_cli('--only', 'dev-baseline,execute-work', '--exclude', 'execute-work'))
        self.assertEqual({p.name for p in self.skills.iterdir()}, {'dev-baseline'})
        self.ok(self.run_cli('--only', 'execute-work'))
        self.ok(self.run_cli('--only', 'execute-work', uninstall=True))
        self.assertTrue((self.skills / 'dev-baseline').exists())
        self.assertFalse((self.skills / 'execute-work').exists())

    def test_unknown_or_path_selection_fails_without_writes(self):
        for name in ['missing', '../outside', '/tmp/escape', 'dev-baseline/..']:
            with self.subTest(name=name):
                self.rejected(self.run_cli('--only', name))
                self.assertFalse(self.home.exists())

    def test_dry_run_never_writes(self):
        self.ok(self.run_cli('--dry-run'))
        self.assertFalse(self.home.exists())
        self.ok(self.run_cli())
        before = self.snapshot()
        self.ok(self.run_cli('--dry-run', uninstall=True))
        self.assertEqual(self.snapshot(), before)

    def test_foreign_conflict_no_partial_writes_even_force(self):
        target = self.skills / 'verification-before-completion'
        target.mkdir(parents=True)
        (target / 'user').write_text('mine')
        before = self.snapshot()
        for args in [(), ('--force',)]:
            self.rejected(self.run_cli(*args))
            self.assertEqual(self.snapshot(), before)

    def test_modified_added_deleted_files_block_install_and_uninstall(self):
        for mutation in ['modified', 'added', 'deleted']:
            with self.subTest(mutation=mutation):
                self.ok(self.run_cli('--force'))
                target = self.skills / 'verification-before-completion'
                if mutation == 'modified':
                    (target / 'assets' / 'data.txt').write_text('local')
                elif mutation == 'added':
                    (target / 'local').write_text('local')
                else:
                    (target / 'SKILL.md').unlink()
                before = self.snapshot()
                self.rejected(self.run_cli())
                self.assertEqual(self.snapshot(), before)
                self.rejected(self.run_cli(uninstall=True))
                self.assertEqual(self.snapshot(), before)
        self.ok(self.run_cli('--force', uninstall=True))

    def test_legacy_marker_needs_force_and_source_independent_uninstall(self):
        target = self.legacy()
        before = self.snapshot()
        self.rejected(self.run_cli('--only', 'rtk', uninstall=True))
        self.assertEqual(self.snapshot(), before)
        self.ok(self.run_cli('--only', 'rtk', '--force', uninstall=True))
        self.assertFalse(target.exists())

    def test_legacy_same_name_overwrite_needs_force(self):
        self.legacy('dev-baseline')
        self.rejected(self.run_cli())
        self.ok(self.run_cli('--force'))
        self.assertIn('manifest', json.loads((self.skills / 'dev-baseline' / MARKER).read_text()))

    def test_prune_only_retired_and_preflight_all(self):
        self.ok(self.run_cli())
        retired = self.legacy()
        before = self.snapshot()
        self.rejected(self.run_cli('--only', 'dev-baseline', '--prune'))
        self.assertEqual(self.snapshot(), before)
        self.ok(self.run_cli('--only', 'dev-baseline', '--prune', '--force'))
        self.assertFalse(retired.exists())
        self.assertEqual({p.name for p in self.skills.iterdir()}, NAMES)

    def test_spoofed_markers_cannot_be_forced(self):
        target = self.legacy('dev-baseline')
        original = json.loads((target / MARKER).read_text())
        for key, value in [('source_repo', '/other'), ('source_name', '../evil'),
                           ('installed_by', 'other'), ('kind', 'plugin')]:
            marker = dict(original, **{key: value})
            (target / MARKER).write_text(json.dumps(marker))
            self.rejected(self.run_cli('--force'))
            self.rejected(self.run_cli('--only', 'dev-baseline', '--force', uninstall=True))
            self.assertTrue(target.exists())

    def test_symlink_source_target_and_marker_are_rejected(self):
        outside = self.tmp / 'outside'
        outside.mkdir()
        (outside / 'SKILL.md').write_text('outside')
        source = self.repo / 'skills' / 'dev-baseline'
        shutil.rmtree(source)
        source.symlink_to(outside, target_is_directory=True)
        self.rejected(self.run_cli('--force'))
        self.assertFalse(self.home.exists())
        source.unlink()
        shutil.copytree(outside, source)
        self.skills.mkdir(parents=True)
        target = self.skills / 'dev-baseline'
        target.symlink_to(outside, target_is_directory=True)
        self.rejected(self.run_cli('--force'))
        self.rejected(self.run_cli('--only', 'dev-baseline', '--force', uninstall=True))
        target.unlink()
        target = self.legacy('dev-baseline')
        marker_text = (target / MARKER).read_text()
        (target / MARKER).unlink()
        marker = outside / 'marker'
        marker.write_text(marker_text)
        (target / MARKER).symlink_to(marker)
        self.rejected(self.run_cli('--force'))
        self.assertEqual((outside / 'SKILL.md').read_text(), 'outside')

    def test_nested_symlink_rejected_without_partial_install(self):
        (self.repo / 'skills' / 'verification-before-completion' / 'link').symlink_to(self.tmp)
        self.rejected(self.run_cli())
        self.assertFalse(self.home.exists())

    def test_dry_run_does_not_write_python_cache(self):
        cache = self.repo / 'scripts' / '__pycache__'
        if cache.exists():
            shutil.rmtree(cache)
        env = os.environ.copy()
        env['HOME'] = str(self.tmp)
        env.pop('PYTHONDONTWRITEBYTECODE', None)
        env['PYTHONPYCACHEPREFIX'] = str(cache)
        result = subprocess.run(['python3', str(self.repo / 'scripts' / f'install-{self.platform}.py'),
                                 f'--{self.platform}-home', str(self.home), '--dry-run'],
                                env=env, text=True, capture_output=True)
        self.ok(result)
        self.assertEqual(list(cache.rglob('skill_installer*.pyc')), [])
        self.assertFalse(self.home.exists())

    def test_home_symlink_rejected(self):
        outside = self.tmp / 'outside'
        outside.mkdir()
        self.home.symlink_to(outside, target_is_directory=True)
        self.rejected(self.run_cli('--force'))
        self.assertEqual(list(outside.iterdir()), [])

    def test_uninstall_when_entire_source_directory_removed(self):
        self.ok(self.run_cli())
        shutil.rmtree(self.repo / 'skills')
        self.ok(self.run_cli(uninstall=True))
        self.assertEqual(list(self.skills.iterdir()), [])

    def test_root_home_rejected(self):
        self.rejected(self.run_cli(f'--{self.platform}-home', '/', '--dry-run'))


class PicodeInstallerTests(InstallerContract, unittest.TestCase):
    @unittest.skipUnless(os.sys.platform == 'darwin', 'macOS system aliases')
    def test_macos_system_alias_destination(self):
        alias_home = '/var' + str(self.home)[len('/private/var'):]
        self.assertTrue(str(self.home).startswith('/private/var/'))
        self.ok(self.run_cli('--picode-home', alias_home, '--only', 'dev-baseline'))
        self.assertTrue((self.skills / 'dev-baseline' / 'SKILL.md').is_file())

    def test_config_directory_collision_rejected_before_writes(self):
        for path in ['picode.md', 'picode.md/subdir']:
            for extra in [(), ('--dry-run',), ('--no-defaults',)]:
                with self.subTest(path=path, extra=extra):
                    self.rejected(self.run_cli('--only', 'dev-baseline', '--skills-dir', path, *extra))
                    self.assertFalse(self.home.exists())

    def test_config_case_variants_rejected_before_writes(self):
        for index, path in enumerate(['PICODE.MD', 'PiCode.md/subdir']):
            for dry in [False, True]:
                home = self.tmp / f'case-{index}-{dry}'
                extra = ['--dry-run'] if dry else []
                self.rejected(self.run_cli('--picode-home', str(home), '--only', 'dev-baseline',
                                           '--skills-dir', path, *extra))
                self.assertFalse(home.exists())

    def test_manual_newline_bytes_preserved(self):
        self.home.mkdir()
        for manual in [b'User notes\r\n\r\n- keep-manual\r\n', b'first\r\nsecond\nlast\r\n']:
            with self.subTest(manual=manual):
                self.config.write_bytes(manual)
                self.ok(self.run_cli('--only', 'dev-baseline'))
                self.assertTrue(self.config.read_bytes().startswith(manual))
                self.ok(self.run_cli(uninstall=True))
                self.assertEqual(self.config.read_bytes(), manual)

    def test_only_one_default_and_manual_content_preserved(self):
        self.home.mkdir()
        manual = '  User notes\n\n- karpathy-guidelines\n\n'
        self.config.write_text(manual)
        result = self.run_cli()
        self.ok(result)
        content = self.config.read_text()
        self.assertTrue(content.startswith(manual))
        block = content.split(START)[1].split(END)[0]
        self.assertIn('- dev-baseline', block)
        self.assertNotIn('- rtk', block)
        self.assertNotIn('- karpathy-guidelines', block)
        self.assertIn('retired', result.stdout.lower())
        self.ok(self.run_cli(uninstall=True))
        self.assertEqual(self.config.read_text(), manual)

    def test_no_default_for_uninstalled_baseline(self):
        self.ok(self.run_cli('--only', 'execute-work'))
        self.assertFalse(self.config.exists())

    def test_partial_uninstall_retains_baseline_default(self):
        self.ok(self.run_cli())
        before = self.config.read_text()
        self.ok(self.run_cli('--only', 'execute-work', uninstall=True))
        self.assertEqual(self.config.read_text(), before)

    def test_manual_baseline_not_duplicated(self):
        self.home.mkdir()
        manual = '- dev-baseline\n\n user\n'
        self.config.write_text(manual)
        self.ok(self.run_cli())
        self.assertEqual(self.config.read_text(), manual)

    def test_config_symlink_and_traversal_preflight(self):
        self.home.mkdir()
        outside = self.tmp / 'config'
        outside.write_text('user')
        self.config.symlink_to(outside)
        self.rejected(self.run_cli())
        self.assertFalse(self.skills.exists())
        self.config.unlink()
        for path in ['../escape', '/', str(self.repo / 'skills')]:
            self.rejected(self.run_cli('--skills-dir', path))
        self.assertEqual(outside.read_text(), 'user')


class RepositoryInstallerTests(unittest.TestCase):
    def test_actual_curated_sources_and_both_wrappers(self):
        self.assertEqual({p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')}, NAMES)
        with tempfile.TemporaryDirectory() as temp:
            tmp = Path(temp).resolve()
            env = dict(os.environ, HOME=str(tmp), PYTHONDONTWRITEBYTECODE='1')
            for platform in ['picode', 'codex']:
                home = tmp / platform
                args = [f'--{platform}-home', str(home)]
                for action in ['install', 'uninstall']:
                    result = subprocess.run([str(ROOT / f'{action}-{platform}.sh'), *args],
                                            env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    if action == 'install':
                        self.assertEqual({p.name for p in (home / 'skills').iterdir()}, NAMES)
                        if platform == 'picode':
                            defaults = (home / 'picode.md').read_text()
                            self.assertEqual([line for line in defaults.splitlines() if line.startswith('- ')],
                                             ['- dev-baseline'])
                    else:
                        self.assertEqual(list((home / 'skills').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
