#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


MARKER_FILE = ".my-skills-install.json"
INSTALLER_ID = "my_skills/install-picode.sh"
DEFAULT_BLOCK_START = "<!-- my_skills:picode-default-skills:start -->"
DEFAULT_BLOCK_END = "<!-- my_skills:picode-default-skills:end -->"


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def expand_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def marker_payload(root: Path, source_name: str, kind: str) -> dict[str, str]:
    return {
        "installed_by": INSTALLER_ID,
        "source_repo": str(root),
        "source_name": source_name,
        "kind": kind,
    }


def read_marker(path: Path) -> dict[str, Any] | None:
    marker_path = path / MARKER_FILE
    if not marker_path.is_file():
        return None
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(marker, dict):
        return None
    return marker


def is_managed_path(path: Path, root: Path, source_name: str, kind: str) -> bool:
    marker = read_marker(path)
    if marker is None:
        return False
    expected = marker_payload(root, source_name, kind)
    return all(marker.get(key) == value for key, value in expected.items())


def discover_standalone_skills(root: Path) -> list[Path]:
    skills = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if (child / ".codex-plugin" / "plugin.json").exists():
            continue
        if (child / "SKILL.md").is_file():
            skills.append(child)
    return skills


def discover_plugin_skills(root: Path) -> list[Path]:
    skills = []
    for plugin in sorted(root.iterdir()):
        if not (plugin / ".codex-plugin" / "plugin.json").is_file():
            continue
        plugin_skills = plugin / "skills"
        if not plugin_skills.is_dir():
            continue
        for child in sorted(plugin_skills.iterdir()):
            if child.is_dir() and (child / "SKILL.md").is_file():
                skills.append(child)
    return skills


def discover_picode_skill_names(root: Path) -> list[str]:
    names = [skill.name for skill in discover_standalone_skills(root) + discover_plugin_skills(root)]
    if len(names) != len(set(names)):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise SystemExit("Duplicate Picode skill name(s): " + ", ".join(duplicates))
    return sorted(names)


def remove_path(
    path: Path,
    root: Path,
    source_name: str,
    kind: str,
    dry_run: bool,
    force: bool,
) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    if not force and not (path.is_dir() and is_managed_path(path, root, source_name, kind)):
        print(f"Skipped unmanaged {kind}: {path}")
        return False
    if dry_run:
        print(f"[dry-run] remove {path}")
        return True
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    return True


def remove_managed_default_block(text: str) -> str:
    start = text.find(DEFAULT_BLOCK_START)
    end = text.find(DEFAULT_BLOCK_END)
    if start == -1 or end == -1 or end < start:
        return text
    end += len(DEFAULT_BLOCK_END)
    if end < len(text) and text[end : end + 1] == "\n":
        end += 1
    if start > 0 and text[start - 1 : start] == "\n":
        start -= 1
    return text[:start].rstrip() + ("\n" if text[:start].strip() and text[end:].strip() else "") + text[end:].lstrip()


def update_picode_md(picode_md: Path, dry_run: bool) -> None:
    if not picode_md.exists():
        return
    existing = picode_md.read_text(encoding="utf-8")
    updated = remove_managed_default_block(existing)
    if updated == existing:
        return
    if dry_run:
        print(f"[dry-run] update {picode_md}")
        return
    picode_md.write_text(updated, encoding="utf-8")


def resolve_skills_home(picode_home: Path, skills_dir: str) -> Path:
    path = Path(skills_dir).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (picode_home / path).resolve()


def parse_args() -> argparse.Namespace:
    home = Path.home()
    parser = argparse.ArgumentParser(description="Uninstall this skill collection from Picode.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without deleting files.")
    parser.add_argument(
        "--picode-home",
        default=os.environ.get("PICODE_HOME", str(home / ".picode")),
        help="Picode home directory. Defaults to $PICODE_HOME or ~/.picode.",
    )
    parser.add_argument(
        "--skills-dir",
        default=os.environ.get("PICODE_SKILLS_DIR", "skills"),
        help="Picode skills directory. Relative paths are resolved under --picode-home.",
    )
    parser.add_argument(
        "--no-defaults",
        action="store_true",
        help="Do not update ~/.picode/picode.md.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove same-named targets even when they do not have this repository's install marker.",
    )
    return parser.parse_args()


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    args = parse_args()
    root = repo_root()
    picode_home = expand_path(args.picode_home)
    skills_home = resolve_skills_home(picode_home, args.skills_dir)
    picode_md = picode_home / "picode.md"
    skill_names = discover_picode_skill_names(root)

    print(f"Repository: {root}")
    print(f"Picode home: {picode_home}")
    print(f"Picode skills: {skills_home}")
    print(f"Picode defaults: {picode_md}")

    print("\nPicode skills:")
    for name in skill_names:
        dst = skills_home / name
        print(f"- {name}")
        remove_path(dst, root, name, "picode-skill", args.dry_run, args.force)

    if not args.no_defaults:
        print("\nDefault-loaded skills:")
        update_picode_md(picode_md, args.dry_run)

    print("\nDone. Start a new Picode session after uninstalling so removed skills are no longer loaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
