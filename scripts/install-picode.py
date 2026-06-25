#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


IGNORE_NAMES = {
    ".git",
    ".DS_Store",
    ".my-skills-install.json",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".codex-plugin",
}

MARKER_FILE = ".my-skills-install.json"
INSTALLER_ID = "my_skills/install-picode.sh"
DEFAULT_PICODE_SKILLS = [
    "dev-baseline",
    "karpathy-guidelines",
    "rtk",
]
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


def copy_ignore(_: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in IGNORE_NAMES or name.endswith(".pyc"):
            ignored.add(name)
    return ignored


def ensure_can_replace(dst: Path, root: Path, source_name: str, kind: str, force: bool) -> None:
    if not dst.exists() and not dst.is_symlink():
        return
    if force:
        return
    if dst.is_dir() and is_managed_path(dst, root, source_name, kind):
        return
    raise SystemExit(
        f"Refusing to overwrite existing {kind} without current-repo marker: {dst}. "
        "Use --force to take ownership and replace it."
    )


def replace_tree(
    src: Path,
    dst: Path,
    root: Path,
    source_name: str,
    kind: str,
    dry_run: bool,
    force: bool,
) -> None:
    ensure_can_replace(dst, root, source_name, kind, force)
    if dry_run:
        print(f"[dry-run] sync {src} -> {dst}")
        print(f"[dry-run] write {dst / MARKER_FILE}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.parent / f".{dst.name}.tmp-{os.getpid()}"
    if tmp.exists():
        shutil.rmtree(tmp)

    shutil.copytree(src, tmp, ignore=copy_ignore)
    (tmp / MARKER_FILE).write_text(
        json.dumps(marker_payload(root, source_name, kind), indent=2) + "\n",
        encoding="utf-8",
    )

    if dst.exists() or dst.is_symlink():
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)

    tmp.rename(dst)


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


def discover_picode_skills(root: Path) -> list[Path]:
    skills = discover_standalone_skills(root) + discover_plugin_skills(root)
    by_name: dict[str, Path] = {}
    for skill in skills:
        existing = by_name.get(skill.name)
        if existing is not None:
            raise SystemExit(f"Duplicate Picode skill name '{skill.name}': {existing} and {skill}")
        by_name[skill.name] = skill
    return skills


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


def render_default_block(default_skills: list[str]) -> str:
    lines = [
        DEFAULT_BLOCK_START,
        "由 my_skills 一键安装维护。Picode 新会话补充默认加载以下 skills：",
        "",
    ]
    lines.extend(f"- {name}" for name in default_skills)
    lines.append(DEFAULT_BLOCK_END)
    return "\n".join(lines) + "\n"


def has_skill_bullet(text: str, skill_name: str) -> bool:
    return any(line.strip() == f"- {skill_name}" for line in text.splitlines())


def update_picode_md(picode_md: Path, default_skills: list[str], dry_run: bool) -> None:
    existing = picode_md.read_text(encoding="utf-8") if picode_md.exists() else ""
    base = remove_managed_default_block(existing).rstrip()
    missing = [name for name in default_skills if not has_skill_bullet(base, name)]
    updated = base + ("\n" if base else "")
    if missing:
        updated = (base + "\n\n" if base else "") + render_default_block(missing)
    if dry_run:
        print(f"[dry-run] update {picode_md}")
        return
    picode_md.parent.mkdir(parents=True, exist_ok=True)
    picode_md.write_text(updated, encoding="utf-8")


def resolve_skills_home(picode_home: Path, skills_dir: str) -> Path:
    path = Path(skills_dir).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (picode_home / path).resolve()


def parse_args() -> argparse.Namespace:
    home = Path.home()
    parser = argparse.ArgumentParser(description="Install this skill collection for Picode.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing files.")
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
        help="Do not update ~/.picode/picode.md with default auto-loaded skills.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite same-named targets that do not have this repository's install marker.",
    )
    return parser.parse_args()


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    args = parse_args()
    root = repo_root()
    picode_home = expand_path(args.picode_home)
    skills_home = resolve_skills_home(picode_home, args.skills_dir)
    picode_md = picode_home / "picode.md"
    skills = discover_picode_skills(root)

    print(f"Repository: {root}")
    print(f"Picode home: {picode_home}")
    print(f"Picode skills: {skills_home}")
    print(f"Picode defaults: {picode_md}")

    print("\nPicode skills:")
    for skill in skills:
        dst = skills_home / skill.name
        print(f"- {skill.name}")
        replace_tree(skill, dst, root, skill.name, "picode-skill", args.dry_run, args.force)

    if not args.no_defaults:
        print("\nDefault-loaded skills:")
        for name in DEFAULT_PICODE_SKILLS:
            print(f"- {name}")
        update_picode_md(picode_md, DEFAULT_PICODE_SKILLS, args.dry_run)

    print("\nDone. Start a new Picode session after installing so new skills are picked up.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
