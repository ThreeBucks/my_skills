#!/usr/bin/env python3
"""Remove selected repo-marked Codex skills; legacy plugins stay untouched."""
import sys
sys.dont_write_bytecode = True
from skill_installer import main

if __name__ == '__main__':
    raise SystemExit(main('codex', uninstall=True))
