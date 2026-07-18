#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RULES = {
    'Never use em-dash': '- Never use em-dash `—`, en-dash `–`, or smart quotes `“”‘’`. Always use ASCII `-` for dashes and `"` `\'` for quotes. Applies to code, files, and chat.',
}

MIN_EVO_VERSION = (0, 12, 2)
EVO_REPO = Path(os.environ.get('EVO_CLI_REPO', str(Path.home() / 'github' / 'evo-cli')))


def install_rules():
    p = Path.home() / '.claude' / 'CLAUDE.md'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)
    content = p.read_text(encoding='utf-8')
    if '# Code style' not in content:
        content += '\n# Code style\n\n'
    added = 0
    for marker, rule in RULES.items():
        if marker not in content:
            content += rule + '\n'
            added += 1
    p.write_text(content, encoding='utf-8')
    if added:
        print(f'Added {added} rule(s) to {p}')
    else:
        print(f'Already installed: {p}')


def evo_version():
    evo = shutil.which('evo')
    if evo is None:
        return None
    result = subprocess.run([evo, '--version'], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', result.stdout)
    return tuple(int(part) for part in match.groups()) if match else None


def pip_install(*args):
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or '').strip().splitlines()
        print(f'  failed: {detail[-1] if detail else "unknown error"}')
    return result.returncode == 0


def fmt(version):
    return '.'.join(str(part) for part in version) if version else 'not installed'


def install_evo():
    current = evo_version()
    if current and current >= MIN_EVO_VERSION:
        print(f'evo-cli {fmt(current)} already satisfies >= {fmt(MIN_EVO_VERSION)}')
        return True

    print(f'evo-cli {fmt(current)} < {fmt(MIN_EVO_VERSION)}, installing from PyPI')
    pip_install('--upgrade', 'evo_cli')

    current = evo_version()
    if current and current >= MIN_EVO_VERSION:
        print(f'evo-cli {fmt(current)} installed from PyPI')
        return True

    if not EVO_REPO.is_dir():
        print(f'PyPI has {fmt(current)}; local repo {EVO_REPO} not found')
        print(f'  clone it: git clone https://github.com/maycuatroi/evo-cli {EVO_REPO}')
        print('  or set EVO_CLI_REPO to its path, then re-run this script')
        return False

    print(f'PyPI has {fmt(current)}; falling back to editable install from {EVO_REPO}')
    pip_install('-e', str(EVO_REPO))

    current = evo_version()
    if current and current >= MIN_EVO_VERSION:
        print(f'evo-cli {fmt(current)} installed from {EVO_REPO}')
        return True

    print(f'evo-cli is {fmt(current)}, still below {fmt(MIN_EVO_VERSION)}')
    print(f'  pull the latest evo-cli and re-run: git -C {EVO_REPO} pull')
    return False


def verify_cred():
    evo = shutil.which('evo')
    if evo is None:
        return False
    result = subprocess.run([evo, 'cred', '--help'], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print('evo is installed but `evo cred` is missing - the credentials-utils skill will not work')
        return False
    print('`evo cred` is available; credentials-utils skill is ready')
    return True


def main():
    install_rules()
    if not install_evo():
        sys.exit(1)
    if not verify_cred():
        sys.exit(1)


if __name__ == '__main__':
    main()
