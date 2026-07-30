#!/usr/bin/env python3
import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
SOURCE = REPO / 'skills'

IGNORED_DIRS = {'__pycache__', '.git', '.claude', '.venv', 'node_modules'}
IGNORED_FILES = {'.skillfish.json', '.DS_Store'}
IGNORED_SUFFIXES = {'.pyc', '.pyo'}

TARGETS = {
    'claude': Path.home() / '.claude' / 'skills',
    'opencode': Path.home() / '.opencode' / 'skills',
}


def is_ignored(rel):
    if any(part in IGNORED_DIRS for part in rel.parts):
        return True
    if rel.name in IGNORED_FILES:
        return True
    return rel.suffix in IGNORED_SUFFIXES


def iter_files(root):
    if not root.is_dir():
        return []
    found = []
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if is_ignored(rel):
            continue
        found.append(rel)
    return sorted(found)


def source_skills(names=None):
    if not SOURCE.is_dir():
        return []
    skills = sorted(p.name for p in SOURCE.iterdir() if p.is_dir() and p.name not in IGNORED_DIRS)
    if names:
        wanted = set(names)
        unknown = wanted - set(skills)
        if unknown:
            print(f'unknown skill(s): {", ".join(sorted(unknown))}', file=sys.stderr)
            sys.exit(2)
        skills = [s for s in skills if s in wanted]
    return skills


def normalized(path):
    raw = path.read_bytes()
    try:
        raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw
    return raw.replace(b'\r\n', b'\n').replace(b'\r', b'\n')


def same_content(a, b):
    try:
        return normalized(a) == normalized(b)
    except OSError:
        return False


def diff_skill(skill, dest_root):
    src = SOURCE / skill
    dest = dest_root / skill
    src_files = set(iter_files(src))
    dest_files = set(iter_files(dest))
    missing = sorted(src_files - dest_files)
    extra = sorted(dest_files - src_files)
    differs = sorted(
        rel for rel in sorted(src_files & dest_files) if not same_content(src / rel, dest / rel)
    )
    return missing, differs, extra


def report(skill, missing, differs, extra):
    lines = []
    for rel in missing:
        lines.append(f'  missing at target: {skill}/{rel.as_posix()}')
    for rel in differs:
        lines.append(f'  content differs:   {skill}/{rel.as_posix()}')
    for rel in extra:
        lines.append(f'  only at target:    {skill}/{rel.as_posix()}')
    return lines


def uncommitted_sources():
    result = subprocess.run(
        ['git', '-C', str(REPO), 'status', '--porcelain', '--', 'skills'],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


def backup(dest_root, skill, stamp):
    dest = dest_root / skill
    if not dest.is_dir():
        return None
    holder = dest_root / f'.backup-{stamp}'
    target = holder / skill
    target.parent.mkdir(parents=True, exist_ok=True)
    for rel in iter_files(dest):
        copy_to = target / rel
        copy_to.parent.mkdir(parents=True, exist_ok=True)
        copy_to.write_bytes((dest / rel).read_bytes())
    return target


def write_file(src, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(normalized(src))


def sync_skill(skill, dest_root, missing, differs, extra):
    src = SOURCE / skill
    dest = dest_root / skill
    for rel in missing + differs:
        write_file(src / rel, dest / rel)
    for rel in extra:
        (dest / rel).unlink(missing_ok=True)
    for path in sorted(dest.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def resolve_targets(selected):
    if selected == 'all':
        chosen = list(TARGETS.items())
    else:
        chosen = [(selected, TARGETS[selected])]
    live = []
    for name, root in chosen:
        if root.parent.is_dir():
            live.append((name, root))
        else:
            print(f'[{name}] skipped: {root.parent} does not exist on this machine')
    return live


def main():
    parser = argparse.ArgumentParser(
        description='Install the skills in this repo into the agent runtimes on this machine.'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='compare only, exit non-zero and list every file that differs',
    )
    parser.add_argument(
        '--target',
        choices=['all', *TARGETS],
        default='all',
        help='runtime to install into (default: all)',
    )
    parser.add_argument(
        '--skill',
        action='append',
        help='limit to one skill, repeatable (default: every skill in skills/)',
    )
    parser.add_argument(
        '--dest',
        help='override the destination root, for testing',
    )
    args = parser.parse_args()

    skills = source_skills(args.skill)
    if not skills:
        print(f'no skills found under {SOURCE}', file=sys.stderr)
        return 2

    if args.dest:
        targets = [('dest', Path(args.dest).expanduser().resolve())]
    else:
        targets = resolve_targets(args.target)
    if not targets:
        print('no runtime found to install into', file=sys.stderr)
        return 2

    dirty = uncommitted_sources()
    if dirty:
        print(f'warning: {len(dirty)} uncommitted path(s) under skills/, installing the working tree')
        for path in dirty[:10]:
            print(f'  {path}')

    drift = 0
    stamp = time.strftime('%Y%m%dT%H%M%S')
    for name, root in targets:
        lines = []
        pending = []
        for skill in skills:
            missing, differs, extra = diff_skill(skill, root)
            if missing or differs or extra:
                lines.extend(report(skill, missing, differs, extra))
                pending.append((skill, missing, differs, extra))
        if not pending:
            print(f'[{name}] {root}: in sync ({len(skills)} skills)')
            continue
        drift += len(lines)
        print(f'[{name}] {root}: {len(lines)} file(s) differ across {len(pending)} skill(s)')
        for line in lines:
            print(line)
        if args.check:
            continue
        saved = []
        for skill, missing, differs, extra in pending:
            kept = backup(root, skill, stamp)
            if kept:
                saved.append(kept)
            sync_skill(skill, root, missing, differs, extra)
        if saved:
            print(f'[{name}] backed up {len(saved)} skill(s) to {root / f".backup-{stamp}"}')
        print(f'[{name}] installed {len(pending)} skill(s)')

    if args.check:
        if drift:
            print(f'out of sync: {drift} file(s)')
            return 1
        print('in sync')
        return 0

    remaining = 0
    for name, root in targets:
        left = 0
        for skill in skills:
            missing, differs, extra = diff_skill(skill, root)
            left += len(missing) + len(differs) + len(extra)
        remaining += left
        if left:
            print(f'[{name}] still out of sync after install: {left} file(s)', file=sys.stderr)
    return 1 if remaining else 0


if __name__ == '__main__':
    sys.exit(main())
