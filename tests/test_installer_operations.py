from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from test_picode_installers import InstallerContract, MARKER, START


class OperationFixture:
    platform = 'picode'
    setUp = InstallerContract.setUp
    run_cli = InstallerContract.run_cli
    ok = InstallerContract.ok
    rejected = InstallerContract.rejected
    legacy = InstallerContract.legacy
    snapshot = InstallerContract.snapshot


class OperationsContract:
    def test_corrupt_source_never_pruned(self):
        self.ok(self.run_cli())
        source = self.repo / 'skills' / 'execute-work' / 'SKILL.md'
        for content in [None, 'no frontmatter', '---\nname: wrong\n---\n']:
            if content is None:
                source.unlink()
            else:
                source.write_text(content)
            before = self.snapshot()
            result = self.run_cli('--only', 'dev-baseline', '--prune', '--force')
            self.rejected(result)
            self.assertIn('execute-work', result.stdout + result.stderr)
            self.assertEqual(self.snapshot(), before)

    def test_unselected_corrupt_tree_blocks_all_mutations(self):
        retired = self.legacy('rtk')
        bad = self.repo / 'skills' / 'execute-work' / 'assets' / 'unsafe-link'
        bad.symlink_to(self.tmp / 'missing')
        before = self.snapshot()
        result = self.run_cli('--only', 'dev-baseline', '--prune', '--force')
        self.rejected(result)
        self.assertIn('unsafe-link', result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(retired.exists())
        self.assertFalse((self.skills / 'dev-baseline').exists())

    def test_unknown_missing_source_retained_by_prune(self):
        target = self.legacy('not-a-retired-skill')
        result = self.run_cli('--prune', '--force')
        self.ok(result)
        self.assertTrue(target.exists())
        self.assertIn('not-a-retired-skill', result.stdout)
        self.assertIn('Warning', result.stdout)

    def test_mode_changes_require_confirmation(self):
        for relative in ['.', 'assets', 'assets/data.txt']:
            self.ok(self.run_cli('--only', 'dev-baseline', '--force'))
            target = self.skills / 'dev-baseline' / relative
            original = target.stat().st_mode & 0o777
            target.chmod(original ^ 0o010)
            result = self.run_cli('--only', 'dev-baseline')
            self.rejected(result)
            self.assertIn('mode', result.stdout + result.stderr)
            self.rejected(self.run_cli('--only', 'dev-baseline', uninstall=True))
            target.chmod(original)

    def test_v1_is_legacy_even_with_matching_hashes(self):
        self.ok(self.run_cli('--only', 'dev-baseline'))
        path = self.skills / 'dev-baseline' / MARKER
        marker = json.loads(path.read_text())
        marker['manifest_version'] = 1
        path.write_text(json.dumps(marker))
        result = self.run_cli('--only', 'dev-baseline')
        self.rejected(result)
        self.assertIn('legacy', (result.stdout + result.stderr).lower())
        self.ok(self.run_cli('--only', 'dev-baseline', '--force'))

    def test_repo_move_uninstall_preserves_skills_and_config(self):
        self.ok(self.run_cli())
        before = self.snapshot()
        moved = self.tmp / 'moved'
        self.repo.rename(moved)
        self.repo = moved
        result = self.run_cli('--force', uninstall=True)
        self.rejected(result)
        self.assertIn('source mismatch', (result.stdout + result.stderr).lower())
        self.assertEqual(self.snapshot(), before)

    def test_multiple_conflicts_reported_no_writes(self):
        for name in ['dev-baseline', 'execute-work']:
            (self.skills / name).mkdir(parents=True)
        before = self.snapshot()
        result = self.run_cli()
        self.rejected(result)
        self.assertIn('dev-baseline', result.stdout)
        self.assertIn('execute-work', result.stdout)
        self.assertIn('summary', result.stdout.lower())
        self.assertEqual(self.snapshot(), before)

    def test_unrelated_foreign_anomalies_only_warn(self):
        self.skills.mkdir(parents=True)
        (self.skills / 'foreign-link').symlink_to(self.tmp / 'missing')
        bad = self.skills / 'bad-marker'
        bad.mkdir()
        (bad / MARKER).write_text('not json')
        result = self.run_cli('--only', 'dev-baseline')
        self.ok(result)
        self.assertIn('foreign-link', result.stdout)
        self.assertIn('bad-marker', result.stdout)
        self.assertIn('Warning', result.stdout)
        self.rejected(self.run_cli('--only', 'foreign-link', '--force', uninstall=True))
        self.rejected(self.run_cli('--only', 'bad-marker', '--force', uninstall=True))

    def test_suspicious_repo_owned_marker_is_conflict(self):
        target = self.legacy('execute-work')
        marker = json.loads((target / MARKER).read_text())
        marker['source_name'] = 'other'
        (target / MARKER).write_text(json.dumps(marker))
        self.rejected(self.run_cli('--only', 'dev-baseline', '--force'))
        self.assertFalse((self.skills / 'dev-baseline').exists())

    def test_identical_install_is_noop(self):
        self.ok(self.run_cli())
        paths = [self.skills, *self.skills.rglob('*')]
        before = {str(p): (p.stat().st_ino, p.stat().st_mtime_ns) for p in paths}
        result = self.run_cli()
        self.ok(result)
        self.assertIn('unchanged', result.stdout)
        self.assertEqual(before, {str(p): (p.stat().st_ino, p.stat().st_mtime_ns) for p in paths})

    def test_repeat_uninstall_known_names_absent(self):
        for name in ['dev-baseline', 'rtk']:
            result = self.run_cli('--only', name, uninstall=True)
            self.ok(result)
            self.assertIn('already absent', result.stdout)
        self.rejected(self.run_cli('--only', 'dev-baselin', uninstall=True))
        self.assertFalse(self.home.exists())

    def test_modified_file_reason_and_same_dryrun_list(self):
        self.ok(self.run_cli('--only', 'dev-baseline'))
        (self.skills / 'dev-baseline' / 'assets' / 'data.txt').write_text('local secret')
        dry = self.run_cli('--dry-run', '--only', 'dev-baseline')
        real = self.run_cli('--only', 'dev-baseline')
        self.rejected(dry)
        self.rejected(real)
        self.assertEqual(dry.stdout, real.stdout)
        self.assertIn('assets/data.txt', real.stdout)
        self.assertIn('modified', real.stdout)
        self.assertNotIn('local secret', real.stdout)


class PicodeOperationsTests(OperationsContract, OperationFixture, unittest.TestCase):
    def test_no_newline_config_roundtrip(self):
        self.home.mkdir()
        for manual in [b'user notes', b'a\r\nb\nc', b'a\r']:
            self.config.write_bytes(manual)
            self.ok(self.run_cli('--only', 'dev-baseline'))
            installed = self.config.read_bytes()
            self.assertIn(b'\n' + START.encode(), installed)
            self.assertTrue(installed.startswith(manual))
            self.ok(self.run_cli(uninstall=True))
            self.assertEqual(self.config.read_bytes(), manual)

    def test_managed_retired_reference_not_warned(self):
        from test_picode_installers import END
        self.home.mkdir()
        self.config.write_text(START + '\n- rtk\n' + END + '\n')
        result = self.run_cli('--only', 'dev-baseline')
        self.ok(result)
        self.assertNotIn('retired default reference', result.stdout)

    def invoke_in_process(self, failure):
        spec = importlib.util.spec_from_file_location('installer_under_test', self.repo / 'scripts' / 'skill_installer.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        output = io.StringIO()
        argv = ['installer', '--picode-home', str(self.home), '--only', 'dev-baseline']
        with patch.object(sys, 'argv', argv), patch.object(Path, 'rename', failure), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = module.main('picode')
        return code, output.getvalue()

    def test_successful_update_cleans_staging_and_backup(self):
        self.ok(self.run_cli('--only', 'dev-baseline'))
        source = self.repo / 'skills' / 'dev-baseline' / 'assets' / 'data.txt'
        source.write_text('updated source')
        result = self.run_cli('--only', 'dev-baseline')
        self.ok(result)
        self.assertIn('update / install', result.stdout)
        self.assertEqual((self.skills / 'dev-baseline' / 'assets' / 'data.txt').read_text(), 'updated source')
        self.assertFalse(list(self.home.rglob('.my-skills-stage-*')))
        self.assertFalse(list(self.home.rglob('.my-skills-backup-*')))

    def test_staging_target_change_rejected_before_replacement(self):
        self.ok(self.run_cli('--only', 'dev-baseline'))
        target = self.skills / 'dev-baseline' / 'assets' / 'data.txt'
        source = self.repo / 'skills' / 'dev-baseline' / 'assets' / 'data.txt'
        source.write_text('updated source')
        original = shutil.copytree
        def copying(src, dst, *args, **kwargs):
            result = original(src, dst, *args, **kwargs)
            if Path(src).name == 'dev-baseline':
                target.write_text('concurrent local edit')
            return result
        with patch.object(shutil, 'copytree', copying):
            code, output = self.invoke_in_process(Path.rename)
        self.assertEqual(code, 1, output)
        self.assertIn('Target changed', output)
        self.assertEqual(target.read_text(), 'concurrent local edit')
        self.assertFalse(list(self.home.rglob('.my-skills-stage-*')))

    def test_staging_source_change_rejected_before_replacement(self):
        self.ok(self.run_cli('--only', 'dev-baseline'))
        before = self.snapshot()
        source = self.repo / 'skills' / 'dev-baseline' / 'assets' / 'data.txt'
        source.write_text('updated source')
        original = shutil.copytree
        def copying(src, dst, *args, **kwargs):
            result = original(src, dst, *args, **kwargs)
            if Path(src).name == 'dev-baseline':
                source.write_text('concurrent source edit')
            return result
        with patch.object(shutil, 'copytree', copying):
            code, output = self.invoke_in_process(Path.rename)
        self.assertEqual(code, 1, output)
        self.assertIn('Source changed', output)
        self.assertEqual(self.snapshot(), before)

    def test_failed_promotion_restores_old_tree(self):
        self.ok(self.run_cli('--only', 'dev-baseline'))
        before = self.snapshot()
        (self.repo / 'skills' / 'dev-baseline' / 'SKILL.md').write_text('---\nname: dev-baseline\n---\nnew')
        original = Path.rename
        def rename(path, target):
            if path.name == 'dev-baseline' and '.my-skills-stage-' in str(path.parent):
                raise OSError('injected promotion failure')
            return original(path, target)
        code, output = self.invoke_in_process(rename)
        self.assertEqual(code, 1, output)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(any('.my-skills-' in p.name for p in self.home.rglob('*') if p.is_dir()))

    def test_failed_restore_keeps_backup_and_reports_location(self):
        self.ok(self.run_cli('--only', 'dev-baseline'))
        old_bytes = (self.skills / 'dev-baseline' / 'SKILL.md').read_bytes()
        config = self.config.read_bytes()
        (self.repo / 'skills' / 'dev-baseline' / 'SKILL.md').write_text('---\nname: dev-baseline\n---\nnew')
        original = Path.rename
        def rename(path, target):
            if '.my-skills-stage-' in str(path.parent) or '.my-skills-backup-' in str(path.parent):
                raise OSError('injected promotion/restore failure')
            return original(path, target)
        code, output = self.invoke_in_process(rename)
        self.assertEqual(code, 1, output)
        backups = list(self.home.parent.glob('.my-skills-backup-*')) + list(self.home.rglob('.my-skills-backup-*'))
        self.assertEqual(len(backups), 1, output)
        self.assertIn(str(backups[0]), output)
        self.assertEqual((backups[0] / 'dev-baseline' / 'SKILL.md').read_bytes(), old_bytes)
        self.assertEqual(self.config.read_bytes(), config)
        self.assertFalse(list(self.home.rglob('.my-skills-stage-*')))


class CodexOperationsTests(OperationsContract, OperationFixture, unittest.TestCase):
    platform = 'codex'
