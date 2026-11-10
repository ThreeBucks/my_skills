"""Shared, local-only installers. No plugin/Hub/RTK configuration is changed."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

MARKER = '.my-skills-install.json'
START = '<!-- my_skills:picode-default-skills:start -->'
END = '<!-- my_skills:picode-default-skills:end -->'
SEPARATOR = '<!-- my_skills:inserted-leading-newline -->'
NAME = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
CURRENT_NAMES = frozenset({
    'dev-baseline', 'design-workflow', 'execute-work', 'systematic-debugging',
    'test-driven-development', 'code-review-workflow', 'doc-coauthoring',
    'verification-before-completion',
})
# Explicit migration inventory: the former 24 entries minus retained names.
RETIRED_NAMES = frozenset({
    'karpathy-guidelines', 'using-superpowers', 'rtk', 'adadnn-dev-workflow',
    'brainstorming', 'writing-plans', 'improve-codebase-architecture',
    'executing-plans', 'subagent-driven-development', 'dispatching-parallel-agents',
    'using-git-worktrees', 'diagnose', 'requesting-code-review',
    'receiving-code-review', 'finishing-a-development-branch',
    'systems-code-research-doc', 'planning-with-files', 'agent-skill-creator',
    'writing-skills',
})
RETIRED_DEFAULTS = {'karpathy-guidelines', 'rtk', 'using-superpowers'}


def fail(message: str) -> None:
    raise ValueError(message)


def checked_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if '..' in path.parts:
        fail(f'Path traversal is not allowed: {path}')
    path = Path(os.path.abspath(path))
    # macOS exposes these OS-owned aliases; never resolve arbitrary user links.
    if sys.platform == 'darwin':
        for alias, canonical in [('/var', '/private/var'), ('/tmp', '/private/tmp')]:
            prefix = Path(alias)
            if (path == prefix or prefix in path.parents) and prefix.is_symlink():
                if os.readlink(prefix) in (canonical, canonical.lstrip('/')):
                    path = Path(canonical) / path.relative_to(prefix)
                break
    for part in [path, *path.parents]:
        if part.is_symlink():
            fail(f'Symlink path is not allowed: {part}')
    return path


def destination(value: str | Path, root: Path) -> Path:
    path = checked_path(value)
    if path == Path(path.anchor) or path == Path.home().resolve():
        fail(f'Unsafe root/home destination: {path}')
    if path == root or root in path.parents or path in root.parents:
        fail(f'Destination overlaps repository: {path}')
    return path


def tree_manifest(path: Path) -> dict:
    """Version 2 includes root, empty directories, regular modes and file hashes."""
    checked_path(path)
    if not path.is_dir():
        fail(f'Expected a directory: {path}')
    manifest = {'.': {'type': 'directory', 'mode': stat.S_IMODE(path.stat().st_mode)}}

    def visit(directory: Path) -> None:
        # Do not recurse into links, including on Python versions whose glob differs.
        for entry in sorted(directory.iterdir()):
            relative = entry.relative_to(path).as_posix()
            mode = entry.lstat().st_mode
            if stat.S_ISLNK(mode):
                fail(f'Symlink in skill tree: {entry}')
            if relative == MARKER:
                if not stat.S_ISREG(mode):
                    fail(f'Invalid marker file: {entry}')
                continue
            item = {'mode': stat.S_IMODE(mode)}
            if stat.S_ISDIR(mode):
                item['type'] = 'directory'
                manifest[relative + '/'] = item
                visit(entry)
            elif stat.S_ISREG(mode):
                item.update(type='file', sha256=hashlib.sha256(entry.read_bytes()).hexdigest())
                manifest[relative] = item
            else:
                fail(f'Non-regular file in skill tree: {entry}')
    visit(path)
    return manifest


def discover_skills(root: Path) -> dict[str, Path]:
    source = checked_path(root / 'skills')
    if not source.is_dir():
        fail(f'Missing curated skills directory: {source}')
    skills, errors = {}, []
    for child in sorted(source.iterdir()):
        try:
            if child.is_symlink():
                fail(f'Symlink source: {child}')
            if not child.is_dir():
                if child.name in CURRENT_NAMES:
                    fail(f'Current source is not a directory: {child}')
                continue
            if not NAME.fullmatch(child.name):
                fail(f'Unsafe skill name: {child.name}')
            entry = checked_path(child / 'SKILL.md')
            if not entry.is_file():
                fail(f'Missing SKILL.md in curated source: {child}')
            lines = entry.read_text(encoding='utf-8').splitlines()
            if not lines or lines[0] != '---' or '---' not in lines[1:]:
                fail(f'Invalid frontmatter in source: {entry}')
            header = lines[1:lines.index('---', 1)]
            names = [line[5:].strip() for line in header if line.startswith('name:')]
            if len(names) != 1 or names[0] not in (child.name, repr(child.name), '"' + child.name + '"'):
                fail(f'Frontmatter name must match directory {child.name}: {entry}')
            skills[child.name] = child
        except (ValueError, OSError) as exc:
            errors.append(str(exc))
    missing = CURRENT_NAMES - {p.name for p in source.iterdir()}
    if missing:
        errors.append('Missing current source directories: ' + ', '.join(sorted(missing)))
    if errors:
        fail('\n'.join(errors))
    if not skills:
        fail(f'No curated skills found in {source}')
    return skills


def identity(root: Path, name: str, platform: str) -> dict[str, str]:
    return {'installed_by': f'my_skills/install-{platform}.sh',
            'source_repo': str(root), 'source_name': name,
            'kind': 'picode-skill' if platform == 'picode' else 'skill'}


def read_marker(path: Path) -> dict | None:
    marker = path / MARKER
    if marker.is_symlink():
        fail(f'Symlink marker: {marker}')
    if not marker.exists():
        return None
    if not marker.is_file():
        fail(f'Invalid marker: {marker}')
    try:
        value = json.loads(marker.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError):
        fail(f'Invalid marker JSON: {marker}')
    if not isinstance(value, dict):
        fail(f'Invalid marker object: {marker}')
    return value


def same_owner(marker: dict | None, root: Path, name: str, platform: str) -> bool:
    return marker is not None and all(marker.get(k) == v for k, v in identity(root, name, platform).items())


def classify(path: Path, root: Path, platform: str) -> dict:
    """Lightweight ownership scan only: never walk installed content or follow links."""
    result = {'status': 'foreign', 'reason': 'unmanaged path; --force cannot take ownership'}
    if path.is_symlink():
        return dict(result, reason=f'Symlink target: {path}')
    if not path.exists():
        return {'status': 'absent', 'reason': 'already absent'}
    if not path.is_dir():
        return result
    try:
        marker = read_marker(path)
    except (ValueError, OSError) as exc:
        return dict(result, reason=str(exc))
    if same_owner(marker, root, path.name, platform) and NAME.fullmatch(path.name):
        return {'status': 'owned', 'reason': '', 'marker': marker}
    if marker and marker.get('source_repo') == str(root):
        return {'status': 'suspicious', 'reason': f'Invalid or impersonating repo marker: {path}'}
    if marker and marker.get('installed_by') == identity(root, path.name, platform)['installed_by']:
        return {'status': 'source mismatch', 'reason': f'source mismatch: marker belongs to {marker.get("source_repo")!r}; no automatic adoption'}
    return result


def installed_paths(home: Path, root: Path, platform: str) -> dict[str, dict]:
    if not home.exists():
        return {}
    if not home.is_dir():
        fail(f'Skills home is not a directory: {home}')
    return {child.name: classify(child, root, platform) for child in sorted(home.iterdir())}


def manifest_changes(expected: dict, actual: dict) -> list[str]:
    reasons = []
    for name in sorted(expected.keys() | actual.keys()):
        if name not in actual:
            reasons.append(f'{name}: deleted')
        elif name not in expected:
            reasons.append(f'{name}: added')
        elif expected[name] != actual[name]:
            old, new = expected[name], actual[name]
            fields = [key for key in ('type', 'mode', 'sha256')
                      if not isinstance(old, dict) or old.get(key) != new.get(key)]
            reasons.append(f'{name}: changed {", ".join(fields)}')
    return reasons


def managed_state(path: Path, root: Path, platform: str) -> dict:
    entry = classify(path, root, platform)
    if entry['status'] != 'owned':
        fail(entry['reason'])
    actual = tree_manifest(path)  # Symlinks remain forbidden even with --force.
    marker = entry['marker']
    trusted = marker.get('manifest_version') == 2 and isinstance(marker.get('manifest'), dict)
    expected = marker.get('manifest', {}) if trusted else {}
    if trusted:
        trusted = '.' in expected and all(
            isinstance(value, dict) and value.get('type') in ('file', 'directory')
            and type(value.get('mode')) is int
            and (value['type'] != 'file' or isinstance(value.get('sha256'), str))
            for value in expected.values())
    changes = manifest_changes(expected, actual) if trusted else []
    info = path.stat()
    return {'status': 'legacy' if not trusted else ('modified' if changes else 'clean'),
            'reason': '; '.join(changes) if trusted else 'legacy manifest lacks mode-aware verification',
            'snapshot': (info.st_dev, info.st_ino, marker, actual)}


def names_from_args(values: list[str] | None) -> set[str]:
    names = set()
    for value in values or []:
        for name in value.split(','):
            if not NAME.fullmatch(name):
                fail(f'Invalid skill selection: {name!r}')
            names.add(name)
    return names


def select(available: set[str], only: list[str] | None, exclude: list[str] | None) -> set[str]:
    requested = names_from_args(only)
    excluded = names_from_args(exclude)
    unknown = (requested | excluded) - available
    if unknown:
        fail('Unknown skill selection: ' + ', '.join(sorted(unknown)))
    return (requested if only else available) - excluded


def config_update(path: Path, baseline: bool) -> tuple[str, str]:
    checked_path(path)
    if path.exists() and not path.is_file():
        fail(f'Default config is not a regular file: {path}')
    existing = path.read_bytes().decode('utf-8') if path.exists() else ''
    if existing.count(START) != existing.count(END) or existing.count(START) > 1:
        fail(f'Ambiguous managed default block; repair manually: {path}')
    base = existing
    if START in base:
        start, end = base.index(START), base.index(END)
        if end < start:
            fail(f'Malformed managed default block: {path}')
        inserted = SEPARATOR in base[start:end]
        end += len(END)
        if base[end:end + 2] == '\r\n':
            end += 2
        elif base[end:end + 1] == '\n':
            end += 1
        if inserted and start and base[start - 1] == '\n':
            start -= 1
        base = base[:start] + base[end:]
    for name in sorted(RETIRED_DEFAULTS):
        if any(re.fullmatch(r'\s*-\s+' + re.escape(name) + r'\s*', line) for line in base.splitlines()):
            print(f'Warning: retired default reference {name}; user-written references are preserved. Review manually.')
    updated = base
    if baseline and not any(line.strip() == '- dev-baseline' for line in base.splitlines()):
        # Provenance lives inside the managed block; removing it restores exact bytes.
        separator = bool(base and not base.endswith('\n'))
        updated += ('\n' if separator else '') + START + '\n'
        updated += (SEPARATOR + '\n') if separator else ''
        updated += '由 my_skills 维护的新会话默认技能：\n\n- dev-baseline\n' + END + '\n'
    return existing, updated


def parser_for(platform: str, uninstall: bool) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f'{"Uninstall" if uninstall else "Install"} curated skills for {platform}; no plugins are registered.')
    parser.add_argument(f'--{platform}-home', default=os.environ.get(platform.upper() + '_HOME', str(Path.home() / ('.' + platform))))
    parser.add_argument('--skills-dir', default=os.environ.get('PICODE_SKILLS_DIR', 'skills') if platform == 'picode' else 'skills', help='Relative to platform home, or an absolute dedicated directory.')
    parser.add_argument('--only', action='append', help='Select comma-separated names; repeatable.')
    parser.add_argument('--exclude', action='append', help='Exclude comma-separated names; repeatable.')
    parser.add_argument('--dry-run', action='store_true', help='Preflight and print actions without writing.')
    parser.add_argument('--force', action='store_true', help='Confirm modified or legacy content owned by this exact repository path; never adopt foreign paths.')
    parser.add_argument('--no-defaults', action='store_true', help='Leave PiCode default configuration untouched.')
    if not uninstall:
        parser.add_argument('--prune', action='store_true', help='Remove only explicitly retired repo-managed names; keep other missing sources.')
    if platform == 'codex':
        parser.add_argument('--agents-home', help='Compatibility only; marketplace is not changed.')
        parser.add_argument('--plugin-home', help='Compatibility only; legacy plugin files are not changed.')
        parser.add_argument('--no-plugin-remove' if uninstall else '--no-plugin-add', action='store_true', help='Compatibility no-op; plugins are never changed.')
        parser.add_argument('--require-codex-cli', action='store_true', help='Compatibility no-op; no Codex CLI is invoked.')
    return parser


def operation(name: str, status: str, action: str, reason: str, **details) -> dict:
    return dict(name=name, status=status, action=action, reason=reason, **details)


def target_operation(name: str, action: str, skills_home: Path, root: Path,
                     platform: str, force: bool, manifest: dict | None = None) -> dict:
    path = skills_home / name
    entry = classify(path, root, platform)
    status = entry['status']
    if status == 'absent':
        return operation(name, 'new' if action == 'install' else 'absent',
                         action if action == 'install' else 'skip',
                         'new curated skill' if action == 'install' else 'already absent',
                         snapshot=None, manifest=manifest)
    if status != 'owned':
        return operation(name, status, 'conflict', entry['reason'])
    try:
        state = managed_state(path, root, platform)
    except (ValueError, OSError) as exc:
        return operation(name, 'modified', 'conflict', str(exc))
    status, reason = state['status'], state['reason']
    if status in ('legacy', 'modified'):
        if not force:
            action = 'conflict'
            reason += '; inspect then use --force to confirm'
    elif action == 'install':
        status = 'unchanged' if state['snapshot'][3] == manifest else 'update'
        if status == 'unchanged':
            action = 'skip'
        reason = 'matches source and manifest' if status == 'unchanged' else 'curated source changed'
    else:
        status = 'retired' if name in RETIRED_NAMES else 'unchanged'
        reason = 'verified repo-owned tree'
    return operation(name, status, action, reason, snapshot=state['snapshot'], manifest=manifest)


def build_operations(args, uninstall: bool, sources: dict, installed: dict,
                     skills_home: Path, root: Path, platform: str) -> list[dict]:
    # Validate the complete curated distribution before planning destructive migration.
    manifests, source_conflicts = {}, []
    for name, source in sorted(sources.items()):
        try:
            manifests[name] = tree_manifest(source)
        except (ValueError, OSError) as exc:
            source_conflicts.append(operation(name, 'source', 'conflict', str(exc)))
    if source_conflicts:
        return source_conflicts
    owned = {name for name, entry in installed.items() if entry['status'] == 'owned'}
    if uninstall:
        available = set(installed) | CURRENT_NAMES | RETIRED_NAMES
        chosen = select(available, args.only, args.exclude)
        if not args.only:
            chosen &= owned | {n for n, e in installed.items() if e['status'] in ('source mismatch', 'suspicious')}
        additions, removals = set(), chosen
    else:
        additions = select(set(sources), args.only, args.exclude)
        removals = (owned & RETIRED_NAMES) - set(sources) if args.prune else set()
    operations = []
    for name in sorted(additions | removals):
        manifest = manifests.get(name) if name in additions else None
        operations.append(target_operation(name, 'install' if name in additions else 'remove',
                                           skills_home, root, platform, args.force, manifest))
    for name, entry in installed.items():
        if name in additions | removals:
            continue
        status = entry['status']
        if status == 'suspicious' or (uninstall and status == 'source mismatch'):
            operations.append(operation(name, status, 'conflict', entry['reason']))
        elif status != 'owned':
            operations.append(operation(name, status, 'warn', entry['reason']))
        elif not uninstall and name not in sources:
            retired = name in RETIRED_NAMES
            operations.append(operation(name, 'retired' if retired else 'missing source', 'warn',
                                        'retained; inspect and use --prune' if retired else 'retained; not in explicit retired inventory'))
        else:
            operations.append(operation(name, 'unselected', 'skip', 'retained; outside selection'))
    return sorted(operations, key=lambda op: op['name'])


def report_operations(operations: list[dict]) -> bool:
    for op in operations:
        prefix = 'Warning: ' if op['action'] == 'warn' else ''
        print(f'{prefix}{op["name"]}: {op["status"]} / {op["action"]} — {op["reason"]}')
    counts = Counter(op['action'] for op in operations)
    print('Summary: ' + ', '.join(f'{key}={counts[key]}' for key in ('install', 'remove', 'config', 'skip', 'warn', 'conflict')))
    return not counts['conflict']


def recheck_target(op: dict, skills_home: Path, root: Path, platform: str) -> None:
    target = checked_path(skills_home / op['name'])
    if op['snapshot'] is None:
        if target.exists():
            fail(f'Target appeared after preflight: {target}')
    elif managed_state(target, root, platform)['snapshot'] != op['snapshot']:
        fail(f'Target changed after preflight: {target}')


def promote(staged: Path, target: Path, backup_parent: Path) -> None:
    """One-item recovery only; a failed restore must leave its backup intact."""
    if not target.exists():
        staged.rename(target)
        return
    backup = Path(tempfile.mkdtemp(prefix='.my-skills-backup-', dir=backup_parent))
    old = backup / target.name
    try:
        target.rename(old)
    except OSError:
        backup.rmdir()
        raise
    try:
        staged.rename(target)
    except OSError as promotion_error:
        try:
            if target.exists() or target.is_symlink():
                fail(f'Target appeared during recovery: {target}')
            old.rename(target)
        except (OSError, ValueError) as restore_error:
            fail(f'Promotion failed: {promotion_error}; restore failed: {restore_error}. '
                 f'Old skill retained for manual recovery at {backup}')
        backup.rmdir()
        raise
    shutil.rmtree(backup)


def apply_operations(operations: list[dict], sources: dict, skills_home: Path,
                     root: Path, platform: str) -> None:
    additions = [op for op in operations if op['action'] == 'install']
    removals = [op for op in operations if op['action'] == 'remove']
    if additions:
        checked_path(skills_home).mkdir(parents=True, exist_ok=True)
        # Keep staging outside skill discovery where possible, but on the same FS.
        temp_parent = skills_home.parent
        if temp_parent.stat().st_dev != skills_home.stat().st_dev:
            temp_parent = skills_home
        staging = Path(tempfile.mkdtemp(prefix='.my-skills-stage-', dir=temp_parent))
        try:
            for op in additions:
                name = op['name']
                if tree_manifest(sources[name]) != op['manifest']:
                    fail(f'Source changed before staging: {name}')
                staged = staging / name
                shutil.copytree(sources[name], staged, symlinks=True)
                if tree_manifest(staged) != op['manifest'] or tree_manifest(sources[name]) != op['manifest']:
                    fail(f'Source changed during staging: {name}; retry after source edits finish.')
                marker = identity(root, name, platform)
                marker.update(manifest_version=2, manifest=op['manifest'])
                (staged / MARKER).write_text(json.dumps(marker, indent=2) + '\n', encoding='utf-8')
            # Recheck all targets before the first mutation, then again per item.
            for op in additions + removals:
                recheck_target(op, skills_home, root, platform)
            for op in additions:
                recheck_target(op, skills_home, root, platform)
                promote(staging / op['name'], skills_home / op['name'], temp_parent)
        finally:
            shutil.rmtree(staging)
    for op in removals:
        recheck_target(op, skills_home, root, platform)
        shutil.rmtree(skills_home / op['name'])


def run(platform: str, uninstall: bool = False) -> int:
    args = parser_for(platform, uninstall).parse_args()
    root = Path(__file__).resolve().parents[1]
    home = destination(getattr(args, platform + '_home'), root)
    relative = Path(args.skills_dir).expanduser()
    skills_home = destination(relative if relative.is_absolute() else home / relative, root)
    if skills_home == home or skills_home in home.parents:
        fail(f'Skills destination must not be the platform home or its ancestor: {skills_home}')
    config = home / 'picode.md'
    if platform == 'picode':
        config_key = str(config).casefold()
        if any(str(p).casefold() == config_key for p in [skills_home, *skills_home.parents]):
            fail(f'Skills destination collides with default config: {skills_home}')
    if home.exists() and not home.is_dir():
        fail(f'Platform home is not a directory: {home}')
    installed = installed_paths(skills_home, root, platform)
    sources = {} if uninstall else discover_skills(root)
    operations = build_operations(args, uninstall, sources, installed, skills_home, root, platform)
    old_config = new_config = None
    if platform == 'picode' and not args.no_defaults:
        remaining = {n for n, e in installed.items() if e['status'] == 'owned'}
        remaining |= {op['name'] for op in operations if op['action'] == 'install'}
        remaining -= {op['name'] for op in operations if op['action'] == 'remove'}
        try:
            old_config, new_config = config_update(config, 'dev-baseline' in remaining)
            if new_config != old_config:
                operations.append(operation(str(config), 'config', 'config', 'update managed default block'))
        except (ValueError, OSError) as exc:
            operations.append(operation(str(config), 'config', 'conflict', str(exc)))
    if platform == 'codex':
        print('Notice: legacy plugins/marketplace/registrations are untouched, even with --force or --prune. Review and remove old plugins manually; no Codex CLI is invoked.')
    if not report_operations(operations):
        print('No changes applied: resolve conflicts before execution.')
        return 1
    if args.dry_run:
        print('Dry run: no changes applied.')
        return 0
    apply_operations(operations, sources, skills_home, root, platform)
    if new_config != old_config:
        checked_path(config)
        current = config.read_bytes().decode('utf-8') if config.exists() else ''
        if current != old_config:
            fail(f'Default config changed after preflight; left untouched: {config}')
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_bytes(new_config.encode('utf-8'))
    return 0


def main(platform: str, uninstall: bool = False) -> int:
    try:
        return run(platform, uninstall)
    except (ValueError, OSError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
