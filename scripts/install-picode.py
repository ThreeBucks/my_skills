#!/usr/bin/env python3
"""PiCode entry point; installs only direct skills/*/SKILL.md sources."""
import sys
sys.dont_write_bytecode = True
from skill_installer import main

if __name__ == '__main__':
    raise SystemExit(main('picode'))
