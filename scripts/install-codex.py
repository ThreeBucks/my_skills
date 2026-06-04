#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IGNORE_NAMES = {
    ".git",
    ".DS_Store",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def expand_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def copy_ignore(_: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in IGNORE_NAMES or name.endswith(".pyc"):
            ignored.add(name)
    return ignored


def replace_tree(src: Path, dst: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] sync {src} -> {dst}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.parent / f".{dst.name}.tmp-{os.getpid()}"
    if tmp.exists():
        shutil.rmtree(tmp)

    shutil.copytree(src, tmp, ignore=copy_ignore)

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


def discover_plugins(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    plugins = []
    for child in sorted(root.iterdir()):
        manifest_path = child / ".codex-plugin" / "plugin.json"
        if not child.is_dir() or not manifest_path.is_file():
            continue
        manifest = load_json(manifest_path)
        name = manifest.get("name")
        if not isinstance(name, str) or not name:
            raise SystemExit(f"Invalid plugin manifest name: {manifest_path}")
        if child.name != name:
            raise SystemExit(
                f"Plugin folder name '{child.name}' does not match manifest name '{name}'"
            )
        plugins.append((child, manifest))
    return plugins


def with_cachebuster(version: str, stamp: str) -> str:
    base = version.split("+", 1)[0]
    return f"{base}+codex.local-{stamp}"


def update_installed_plugin_manifest(plugin_dir: Path, stamp: str, dry_run: bool) -> None:
    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    manifest = load_json(manifest_path)
    version = manifest.get("version", "0.1.0")
    if not isinstance(version, str) or not version:
        version = "0.1.0"
    manifest["version"] = with_cachebuster(version, stamp)
    write_json(manifest_path, manifest, dry_run)


def update_personal_marketplace(
    marketplace_path: Path,
    plugin_names: list[str],
    dry_run: bool,
) -> str:
    marketplace = load_json(marketplace_path)
    if not marketplace:
        marketplace = {
            "name": "personal",
            "interface": {"displayName": "Personal"},
            "plugins": [],
        }

    marketplace.setdefault("name", "personal")
    marketplace.setdefault("interface", {"displayName": "Personal"})
    plugins = marketplace.setdefault("plugins", [])
    if not isinstance(plugins, list):
        raise SystemExit(f"Invalid marketplace plugins list: {marketplace_path}")

    by_name = {
        entry.get("name"): index
        for index, entry in enumerate(plugins)
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }

    for name in plugin_names:
        entry = {
            "name": name,
            "source": {
                "source": "local",
                "path": f"./plugins/{name}",
            },
            "policy": {
                "installation": "AVAILABLE",
                "authentication": "ON_INSTALL",
            },
            "category": "Coding",
        }
        if name in by_name:
            plugins[by_name[name]] = entry
        else:
            plugins.append(entry)

    write_json(marketplace_path, marketplace, dry_run)
    name = marketplace.get("name")
    if not isinstance(name, str) or not name:
        raise SystemExit(f"Invalid marketplace name: {marketplace_path}")
    return name


def run_codex_plugin_add(
    plugin_names: list[str],
    marketplace_name: str,
    dry_run: bool,
    no_plugin_add: bool,
) -> None:
    if no_plugin_add or not plugin_names:
        return

    codex = shutil.which("codex")
    if codex is None:
        print("codex CLI not found; plugin files and marketplace were synced, but plugin add was skipped.")
        return

    for name in plugin_names:
        cmd = [codex, "plugin", "add", f"{name}@{marketplace_name}"]
        if dry_run:
            print("[dry-run] " + " ".join(cmd))
            continue
        print("$ " + " ".join(cmd))
        subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    home = Path.home()
    parser = argparse.ArgumentParser(description="Install this skill collection for Codex.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing files.")
    parser.add_argument(
        "--codex-home",
        default=os.environ.get("CODEX_HOME", str(home / ".codex")),
        help="Codex home directory. Defaults to $CODEX_HOME or ~/.codex.",
    )
    parser.add_argument(
        "--agents-home",
        default=os.environ.get("AGENTS_HOME", str(home / ".agents")),
        help="Agents home directory for personal marketplace. Defaults to $AGENTS_HOME or ~/.agents.",
    )
    parser.add_argument(
        "--plugin-home",
        default=os.environ.get("CODEX_PLUGIN_HOME", str(home / "plugins")),
        help="Local plugin directory. Defaults to $CODEX_PLUGIN_HOME or ~/plugins. Use non-default paths with --no-plugin-add.",
    )
    parser.add_argument(
        "--no-plugin-add",
        action="store_true",
        help="Only sync plugin files and marketplace; do not run `codex plugin add`.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    codex_home = expand_path(args.codex_home)
    skills_home = codex_home / "skills"
    agents_home = expand_path(args.agents_home)
    marketplace_path = agents_home / "plugins" / "marketplace.json"
    plugin_home = expand_path(args.plugin_home)
    default_plugin_home = expand_path(Path.home() / "plugins")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    if plugin_home != default_plugin_home and not args.no_plugin_add:
        raise SystemExit(
            "Custom --plugin-home is only supported with --no-plugin-add. "
            "Codex personal marketplace entries resolve ./plugins/<name> to ~/plugins/<name>."
        )

    standalone_skills = discover_standalone_skills(root)
    plugins = discover_plugins(root)

    print(f"Repository: {root}")
    print(f"Codex skills: {skills_home}")
    print(f"Codex plugins: {plugin_home}")
    print(f"Marketplace: {marketplace_path}")

    if standalone_skills:
        print("\nStandalone skills:")
        for skill in standalone_skills:
            dst = skills_home / skill.name
            print(f"- {skill.name}")
            replace_tree(skill, dst, args.dry_run)

    plugin_names: list[str] = []
    if plugins:
        print("\nPlugin bundles:")
        for plugin, manifest in plugins:
            name = str(manifest["name"])
            dst = plugin_home / name
            print(f"- {name}")
            replace_tree(plugin, dst, args.dry_run)
            update_installed_plugin_manifest(dst, stamp, args.dry_run)
            plugin_names.append(name)

        marketplace_name = update_personal_marketplace(marketplace_path, plugin_names, args.dry_run)
        run_codex_plugin_add(plugin_names, marketplace_name, args.dry_run, args.no_plugin_add)

    print("\nDone. Start a new Codex thread after installing so new skills and plugins are picked up.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
