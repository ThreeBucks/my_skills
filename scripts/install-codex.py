#!/usr/bin/env python3
"""Codex compatibility entry point; no plugin installation or registration."""
import sys
sys.dont_write_bytecode = True
from skill_installer import main

if __name__ == '__main__':
    raise SystemExit(main('codex'))
