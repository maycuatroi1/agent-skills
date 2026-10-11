"""What a session of a harness carries before anyone types: the files and listings every session loads, measured and
checked for the smells that make context expensive or stale.

``inventory`` reads the files themselves (they are what a proposal edits):

- Claude Code: ``~/.claude/CLAUDE.md``, then ``CLAUDE.md``, ``.claude/CLAUDE.md`` and ``CLAUDE.local.md`` from the
  root up to ``/``, each with the files it imports (``@path``, five levels deep), and the auto memory index
  ``~/.claude/projects/<root>/memory/MEMORY.md``;
- Codex: ``~/.codex/AGENTS.md`` (or ``AGENTS.override.md``) and the root's ``AGENTS.md``;
- the skill listing as the newest session loaded it, each skill with its size, where it lives and whether the window
  used it; the skills of ``~/.agents/skills`` and ``~/.codex/skills`` for Codex;
- hooks and permission rules of the user's and the project's settings.

Smells, per file: lines that carry a date (status written into a map), paragraphs longer than LONG_PARAGRAPH,
backticked paths that resolve nowhere, and lines that two loaded files both hold. Standard library only.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from _sources import claude_home, codex_home, encode_path

LONG_PARAGRAPH = 800  # characters of one paragraph of an always-loaded file
LONG_DESCRIPTION = 500  # characters of one skill's line in the listing
DUPLICATE_MIN = 40  # characters a line needs before two copies of it count
IMPORT_DEPTH = 5
DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
IMPORT = re.compile(r"(?<![\w`@])@((?:~|\.{1,2})?/?[\w.@/-]+)")
BACKTICK = re.compile(r"`([^`\s]{3,200})`")
PATHLIKE = re.compile(
    r"^(?:~|\.{1,2})?/?[\w.@+-]+(?:/[\w.@+-]+)+/?$|^[\w.-]+\.(?:md|py|ya?ml|json|sh|ts|tsx|js|toml|txt)$"
)
QUOTED = re.compile('["\u201c]([^"\u201d]{4,60})["\u201d]')  # straight or curly double quotes
SKILL_LINE = re.compile(r"^- (\S+?): (.*)$")


def tokens_estimate(chars: int) -> int:
    return round(chars / 4)


def _shown(path: Path) -> str:
    text = str(path)
    home = str(Path.home())
    return "~" + text[len(home) :] if text.startswith(home) else text


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _imports(text: str) -> list[str]:
    out = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = re.sub(r"`[^`]*`", "", line)
        out.extend(found.group(1) for found in IMPORT.finditer(stripped))
    return out


def _resolve(name: str, base: Path) -> Path:
    if name.startswith("~"):
        return Path(name).expanduser()
    path = Path(name)
    return path if path.is_absolute() else (base / path)


def instruction_files(root: Path) -> list[dict]:
    """The always-loaded instruction files of ``root``, in load order, each once, with who loads it."""
    found: dict[Path, dict] = {}

    def add(path: Path, runtime: str, scope: str, via: str | None = None, depth: int = 0) -> None:
        path = path.resolve() if path.exists() else path
        text = _read(path) if path.is_file() else None
        if text is None:
            return
        entry = found.get(path)
        if entry is None:
            entry = found[path] = {
                "path": _shown(path),
                "runtimes": [],
                "scope": scope,
                "via": via,
                "_text": text,
                "_abs": path,
            }
        if runtime not in entry["runtimes"]:
            entry["runtimes"].append(runtime)
        if runtime == "claude" and depth < IMPORT_DEPTH:
            for name in _imports(text):
                target = _resolve(name, path.parent)
                if target.is_file():
                    add(target, runtime, "import", via=_shown(path), depth=depth + 1)

    home = claude_home()
    add(home / "CLAUDE.md", "claude", "user")
    chain = [root, *root.parents]
    for folder in reversed(chain):
        add(folder / "CLAUDE.md", "claude", "project")
        add(folder / ".claude" / "CLAUDE.md", "claude", "project")
        add(folder / "CLAUDE.local.md", "claude", "local")
    add(home / "projects" / encode_path(str(root)) / "memory" / "MEMORY.md", "claude", "memory")
    codex = codex_home()
    override = codex / "AGENTS.override.md"
    add(override if override.is_file() else codex / "AGENTS.md", "codex", "user")
    add(root / "AGENTS.md", "codex", "project")
    return list(found.values())


def _smells(entry: dict, root: Path, bases: list[Path]) -> dict:
    text = entry["_text"]
    base = entry["_abs"].parent
    lines = text.splitlines()
    dated = [number for number, line in enumerate(lines, 1) if DATE.search(line)]
    paragraphs = []
    start, size = None, 0
    for number, line in enumerate([*lines, ""], 1):
        if line.strip():
            start = start or number
            size += len(line) + 1
        else:
            if start and size > LONG_PARAGRAPH:
                paragraphs.append({"line": start, "chars": size})
            start, size = None, 0
    unresolved = []
    for number, line in enumerate(lines, 1):
        for found in BACKTICK.finditer(line):
            token = found.group(1).rstrip(".,:;")
            if not PATHLIKE.match(token) or token.startswith(("http", "//")) or any(c in token for c in "<>*{}$#"):
                continue
            candidates = [_resolve(token, folder) for folder in (base, root, *bases)]
            if not any(candidate.exists() for candidate in candidates):
                unresolved.append({"line": number, "path": token})
    return {
        "dated_lines": len(dated),
        "dated_at": dated[:8],
        "long_paragraphs": paragraphs[:8],
        "unresolved_paths": unresolved[:12],
    }


def _duplicates(entries: list[dict]) -> list[dict]:
    """Lines that two files loaded into the same runtime's context both hold: one fact paid for twice."""
    seen: dict[str, list[tuple[dict, int]]] = defaultdict(list)
    for entry in entries:
        for number, line in enumerate(entry["_text"].splitlines(), 1):
            key = re.sub(r"\s+", " ", re.sub(r"^[\s>*#-]+|\s+$", "", line)).lower()
            if len(key) >= DUPLICATE_MIN:
                seen[key].append((entry, number))
    out = []
    for key, places in seen.items():
        shared = [
            (a, b)
            for i, a in enumerate(places)
            for b in places[i + 1 :]
            if a[0] is not b[0] and set(a[0]["runtimes"]) & set(b[0]["runtimes"])
        ]
        if shared:
            at = []
            for entry, number in [place for pair in shared for place in pair]:
                spot = f"{entry['path']}:{number}"
                if spot not in at:
                    at.append(spot)
            out.append({"text": key[:160], "at": at[:6]})
    return out[:20]


def parse_listing(listing: str) -> list[dict]:
    skills = []
    for line in (listing or "").splitlines():
        found = SKILL_LINE.match(line.strip())
        if found:
            skills.append({"name": found.group(1), "chars": len(line), "description": found.group(2)})
    return skills


def _where(name: str, root: Path) -> str:
    if ":" in name:
        return "plugin"
    if (root / ".claude" / "skills" / name / "SKILL.md").is_file():
        return "project"
    if (claude_home() / "skills" / name / "SKILL.md").is_file():
        return "user"
    return "builtin"


def _used(name: str, used: dict[str, int]) -> int:
    short = name.split(":")[-1]
    return max(used.get(name, 0), used.get(short, 0))


def skills_inventory(root: Path, listing: str | None, figures: dict | None) -> dict:
    used = {row["name"]: row["sessions"] for row in (figures or {}).get("skills", [])}
    listed = parse_listing(listing or "")
    rows = []
    for skill in listed:
        rows.append(
            {
                "name": skill["name"],
                "chars": skill["chars"],
                "where": _where(skill["name"], root),
                "sessions_used": _used(skill["name"], used),
            }
        )
    phrases: dict[str, set] = defaultdict(set)
    for skill in listed:
        for found in QUOTED.finditer(skill["description"]):
            phrases[found.group(1).strip().lower()].add(skill["name"])
    overlaps = [{"phrase": phrase, "skills": sorted(names)} for phrase, names in phrases.items() if len(names) >= 2]
    codex_skills = []
    for folder in (Path("~/.agents/skills").expanduser(), codex_home() / "skills"):
        if not folder.is_dir():
            continue
        for skill_file in sorted(folder.glob("*/SKILL.md")):
            head = (_read(skill_file) or "")[:4000]
            description = re.search(r"^description:\s*(.+)$", head, re.M)
            codex_skills.append(
                {
                    "name": skill_file.parent.name,
                    "dir": _shown(folder),
                    "chars": len(description.group(1)) if description else 0,
                }
            )
    total = sum(row["chars"] for row in rows)
    return {
        "listed": len(rows),
        "listing_chars": total,
        "listing_tokens_est": tokens_estimate(total),
        "largest": sorted(rows, key=lambda row: -row["chars"])[:15],
        "long": [row["name"] for row in rows if row["chars"] > LONG_DESCRIPTION],
        "unused": sorted((row for row in rows if row["sessions_used"] == 0), key=lambda row: -row["chars"]),
        "unused_chars": sum(row["chars"] for row in rows if row["sessions_used"] == 0),
        "by_where": {
            where: sum(row["chars"] for row in rows if row["where"] == where)
            for where in sorted({row["where"] for row in rows})
        },
        "overlapping_triggers": overlaps[:20],
        "codex": {"count": len(codex_skills), "chars": sum(row["chars"] for row in codex_skills)},
        "source": "newest Claude Code session that recorded its skill listing" if listing else "none recorded",
    }


def settings_inventory(root: Path) -> dict:
    out = {"hooks": [], "allow_rules": 0, "files": []}
    for path in (
        claude_home() / "settings.json",
        root / ".claude" / "settings.json",
        root / ".claude" / "settings.local.json",
    ):
        text = _read(path)
        if text is None:
            continue
        try:
            data = json.loads(text)
        except ValueError:
            out["files"].append({"path": _shown(path), "error": "not JSON"})
            continue
        out["files"].append({"path": _shown(path)})
        for event, groups in (data.get("hooks") or {}).items():
            for group in groups if isinstance(groups, list) else []:
                for hook in (group or {}).get("hooks") or []:
                    if isinstance(hook, dict):
                        out["hooks"].append(
                            {
                                "event": event,
                                "file": _shown(path),
                                "command": str(hook.get("command") or hook.get("type"))[:200],
                            }
                        )
        allow = ((data.get("permissions") or {}).get("allow")) or []
        out["allow_rules"] += len(allow) if isinstance(allow, list) else 0
    return out


def memory_inventory(root: Path) -> dict:
    folder = claude_home() / "projects" / encode_path(str(root)) / "memory"
    index = folder / "MEMORY.md"
    text = _read(index) or ""
    links = re.findall(r"\]\(([^)]+\.md)\)", text)
    missing = [link for link in links if not (folder / link).is_file()]
    files = sorted(p.name for p in folder.glob("*.md") if p.name != "MEMORY.md") if folder.is_dir() else []
    unindexed = [name for name in files if name not in links]
    return {
        "dir": _shown(folder),
        "files": len(files),
        "index_lines": len(text.splitlines()),
        "index_chars": len(text),
        "missing_targets": missing[:10],
        "unindexed": unindexed[:10],
    }


def inventory(
    root: Path, listing: str | None = None, figures: dict | None = None, bases: list[str] | None = None
) -> dict:
    """``bases``: more folders a relative path in an instruction file may point into, such as the cluster's repos."""
    entries = instruction_files(root)
    folders = [Path(folder) for folder in bases or []]
    files = []
    for entry in entries:
        text = entry["_text"]
        files.append(
            {
                "path": entry["path"],
                "runtimes": entry["runtimes"],
                "scope": entry["scope"],
                "via": entry["via"],
                "chars": len(text),
                "lines": len(text.splitlines()),
                "tokens_est": tokens_estimate(len(text)),
                "smells": _smells(entry, root, folders),
            }
        )
    by_runtime = {
        runtime: sum(f["chars"] for f in files if runtime in f["runtimes"]) for runtime in ("claude", "codex")
    }
    return {
        "root": _shown(root),
        "files": files,
        "chars_by_runtime": by_runtime,
        "duplicates": _duplicates(entries),
        "skills": skills_inventory(root, listing, figures),
        "settings": settings_inventory(root),
        "memory": memory_inventory(root),
    }
