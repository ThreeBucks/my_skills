from __future__ import annotations

import unittest

from test_picode_installers import InstallerContract, NAMES


class CodexInstallerTests(InstallerContract, unittest.TestCase):
    platform = 'codex'

    def test_compatibility_flags_never_touch_plugins_or_marketplace(self):
        plugins = self.tmp / 'plugins'
        old = plugins / 'ok-skills'
        old.mkdir(parents=True)
        sentinel = old / 'SKILL.md'
        sentinel.write_text('old plugin')
        agents = self.tmp / 'agents'
        agents.mkdir()
        marketplace = agents / 'marketplace.json'
        marketplace.write_text('user config')
        args = ('--agents-home', str(agents), '--plugin-home', str(plugins),
                '--require-codex-cli')
        result = self.run_cli(*args, '--no-plugin-add')
        self.ok(result)
        self.assertEqual({p.name for p in self.skills.iterdir()}, NAMES)
        self.assertIn('manual', result.stdout.lower())
        self.ok(self.run_cli(*args, '--no-plugin-remove', '--force', uninstall=True))
        self.assertEqual(sentinel.read_text(), 'old plugin')
        self.assertEqual(marketplace.read_text(), 'user config')
        self.assertFalse(self.config.exists())


if __name__ == '__main__':
    unittest.main()
