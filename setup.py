#!/usr/bin/env python3
from pathlib import Path

RULES = {
    'Never use em-dash': '- Never use em-dash `—`, en-dash `–`, or smart quotes `“”‘’`. Always use ASCII `-` for dashes and `"` `\'` for quotes. Applies to code, files, and chat.',
}


def main():
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


if __name__ == '__main__':
    main()
