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
    ".my-skills-install.json",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

MARKER_FILE = ".my-skills-install.json"
INSTALLER_ID = "my_skills/install-codex.sh"


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


def resolve_codex_cli() -> str | None:
    candidates: list[Path] = []
    env_path = os.environ.get("CODEX_CLI_PATH")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    which_codex = shutil.which("codex")
    if which_codex:
        candidates.append(Path(which_codex))

    candidates.extend(iter_vscode_codex_cli_candidates(Path.home()))
    candidates.append(Path("/Applications/Codex.app/Contents/Resources/codex"))

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def iter_vscode_codex_cli_candidates(home: Path) -> list[Path]:
    roots: list[Path] = []
    agent_folder = os.environ.get("VSCODE_AGENT_FOLDER")
    if agent_folder:
        roots.append(Path(agent_folder).expanduser() / "extensions")

    extensions_dir = os.environ.get("VSCODE_EXTENSIONS")
    if extensions_dir:
        roots.append(Path(extensions_dir).expanduser())

    roots.extend(
        [
            home / ".vscode" / "extensions",
            home / ".vscode-server" / "extensions",
            home / ".vscode-server-insiders" / "extensions",
            home / ".vscode-remote" / "extensions",
        ]
    )

    candidates: list[Path] = []
    seen_roots: set[Path] = set()
    for root in roots:
        root = root.expanduser()
        if root in seen_roots or not root.is_dir():
            continue
        seen_roots.add(root)
        for extension in sorted(root.glob("openai.chatgpt-*"), reverse=True):
            if not extension.is_dir():
                continue
            for binary_name in ("codex", "codex.exe"):
                candidates.extend(sorted(extension.glob(f"bin/**/{binary_name}"), reverse=True))
    return candidates


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
    require_codex_cli: bool = False,
) -> None:
    if no_plugin_add or not plugin_names:
        return

    codex = resolve_codex_cli()
    if codex is None:
        message = (
            "codex CLI not found. Synced skill files, plugin files, and marketplace "
            "metadata. Skipping `codex plugin add`. If plugins do not load in your "
            "Codex runtime, install or expose the codex CLI, set CODEX_CLI_PATH, and rerun."
        )
        if require_codex_cli:
            raise SystemExit(message)
        print(f"Warning: {message}")
        return

    for name in plugin_names:
        cmd = [codex, "plugin", "add", f"{name}@{marketplace_name}"]
        if dry_run:
            print("[dry-run] " + " ".join(cmd))
            continue
        print("$ " + " ".join(cmd))
        subprocess.run(cmd, check=True)

    verify_codex_plugins_installed(codex, plugin_names, marketplace_name)


def verify_codex_plugins_installed(codex: str, plugin_names: list[str], marketplace_name: str) -> None:
    result = subprocess.run(
        [codex, "plugin", "list"],
        check=True,
        text=True,
        capture_output=True,
    )
    output = result.stdout
    missing: list[str] = []

    for name in plugin_names:
        selector = f"{name}@{marketplace_name}"
        matching_lines = [line for line in output.splitlines() if selector in line]
        if not any("(installed" in line for line in matching_lines):
            missing.append(selector)

    if missing:
        raise SystemExit(
            "codex plugin add completed, but these plugins were not reported as installed: "
            + ", ".join(missing)
            + ". Run `codex plugin list` for details."
        )


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
    parser.add_argument(
        "--require-codex-cli",
        action="store_true",
        help="Fail when codex CLI is unavailable instead of skipping `codex plugin add`.",
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
            replace_tree(skill, dst, root, skill.name, "skill", args.dry_run, args.force)

    plugin_names: list[str] = []
    if plugins:
        print("\nPlugin bundles:")
        for plugin, manifest in plugins:
            name = str(manifest["name"])
            dst = plugin_home / name
            print(f"- {name}")
            replace_tree(plugin, dst, root, name, "plugin", args.dry_run, args.force)
            update_installed_plugin_manifest(dst, stamp, args.dry_run)
            plugin_names.append(name)

        marketplace_name = update_personal_marketplace(marketplace_path, plugin_names, args.dry_run)
        run_codex_plugin_add(
            plugin_names,
            marketplace_name,
            args.dry_run,
            args.no_plugin_add,
            args.require_codex_cli,
        )

    print("\nDone. Start a new Codex thread after installing so new skills and plugins are picked up.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
