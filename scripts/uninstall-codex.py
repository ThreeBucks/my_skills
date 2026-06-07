#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

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


def remove_personal_marketplace_entries(
    marketplace_path: Path,
    plugin_names: list[str],
    dry_run: bool,
) -> str:
    marketplace = load_json(marketplace_path)
    if not marketplace:
        return "personal"

    plugins = marketplace.get("plugins")
    if plugins is None:
        return str(marketplace.get("name") or "personal")
    if not isinstance(plugins, list):
        raise SystemExit(f"Invalid marketplace plugins list: {marketplace_path}")

    names = set(plugin_names)
    kept: list[Any] = []
    removed: list[str] = []
    skipped: list[str] = []

    for entry in plugins:
        if not isinstance(entry, dict) or entry.get("name") not in names:
            kept.append(entry)
            continue

        name = str(entry["name"])
        source = entry.get("source")
        expected_path = f"./plugins/{name}"
        if (
            isinstance(source, dict)
            and source.get("source") == "local"
            and source.get("path") == expected_path
        ):
            removed.append(name)
            continue

        kept.append(entry)
        skipped.append(name)

    marketplace["plugins"] = kept
    if removed:
        print("Marketplace entries removed: " + ", ".join(sorted(removed)))
        write_json(marketplace_path, marketplace, dry_run)
    elif skipped:
        print("No matching local marketplace entries removed.")

    for name in sorted(skipped):
        print(f"Skipped marketplace entry with non-matching source: {name}")

    return str(marketplace.get("name") or "personal")


def run_codex_plugin_remove(
    plugin_names: list[str],
    marketplace_name: str,
    dry_run: bool,
    no_plugin_remove: bool,
    require_codex_cli: bool = False,
) -> None:
    if no_plugin_remove or not plugin_names:
        return

    codex = resolve_codex_cli()
    if codex is None:
        message = (
            "codex CLI not found. Removing local files and marketplace metadata; "
            "Skipping `codex plugin remove`. If a Codex runtime still shows these plugins, "
            "install or expose the codex CLI, set CODEX_CLI_PATH, and rerun."
        )
        if require_codex_cli:
            raise SystemExit(message)
        print(f"Warning: {message}")
        return

    for name in plugin_names:
        cmd = [codex, "plugin", "remove", f"{name}@{marketplace_name}"]
        if dry_run:
            print("[dry-run] " + " ".join(cmd))
            continue
        print("$ " + " ".join(cmd))
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"Warning: codex plugin remove failed for {name}@{marketplace_name}; continuing.")


def parse_args() -> argparse.Namespace:
    home = Path.home()
    parser = argparse.ArgumentParser(description="Uninstall this skill collection from Codex.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without deleting files.")
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
        help="Local plugin directory. Defaults to $CODEX_PLUGIN_HOME or ~/plugins. Use non-default paths with --no-plugin-remove.",
    )
    parser.add_argument(
        "--no-plugin-remove",
        action="store_true",
        help="Only remove files and marketplace entries; do not run `codex plugin remove`.",
    )
    parser.add_argument(
        "--require-codex-cli",
        action="store_true",
        help="Fail when codex CLI is unavailable instead of skipping `codex plugin remove`.",
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
    codex_home = expand_path(args.codex_home)
    skills_home = codex_home / "skills"
    agents_home = expand_path(args.agents_home)
    marketplace_path = agents_home / "plugins" / "marketplace.json"
    plugin_home = expand_path(args.plugin_home)
    default_plugin_home = expand_path(Path.home() / "plugins")

    if plugin_home != default_plugin_home and not args.no_plugin_remove:
        raise SystemExit(
            "Custom --plugin-home is only supported with --no-plugin-remove. "
            "Codex personal marketplace entries resolve ./plugins/<name> to ~/plugins/<name>."
        )

    standalone_skills = discover_standalone_skills(root)
    plugins = discover_plugins(root)
    plugin_names = [str(manifest["name"]) for _, manifest in plugins]
    marketplace_name = str(load_json(marketplace_path).get("name") or "personal")

    print(f"Repository: {root}")
    print(f"Codex skills: {skills_home}")
    print(f"Codex plugins: {plugin_home}")
    print(f"Marketplace: {marketplace_path}")

    if standalone_skills:
        print("\nStandalone skills:")
        for skill in standalone_skills:
            dst = skills_home / skill.name
            print(f"- {skill.name}")
            remove_path(dst, root, skill.name, "skill", args.dry_run, args.force)

    if plugin_names:
        print("\nPlugin bundles:")
        for name in plugin_names:
            dst = plugin_home / name
            print(f"- {name}")
            remove_path(dst, root, name, "plugin", args.dry_run, args.force)

    if plugin_names:
        print("\nCodex plugin registrations:")
        for name in plugin_names:
            print(f"- {name}@{marketplace_name}")
        run_codex_plugin_remove(
            plugin_names,
            marketplace_name,
            args.dry_run,
            args.no_plugin_remove,
            args.require_codex_cli,
        )
        remove_personal_marketplace_entries(marketplace_path, plugin_names, args.dry_run)

    print("\nDone. Start a new Codex thread after uninstalling so removed skills and plugins are no longer loaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
