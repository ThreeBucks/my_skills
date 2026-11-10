#!/usr/bin/env python3
"""Remove selected repo-marked PiCode skills, including retired sources."""
import sys
sys.dont_write_bytecode = True
from skill_installer import main

if __name__ == '__main__':
    raise SystemExit(main('picode', uninstall=True))
