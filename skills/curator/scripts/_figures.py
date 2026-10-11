"""The figures of a set of sessions: what the curator counts without any model, so the agent reads numbers with
evidence instead of transcripts.

``compute`` takes the sessions ``_sources.load`` returned and gives one JSON object (FIGURE_KEYS). Every list is
ranked, cut to a few entries, and each entry names its evidence as ``<runtime>:<session>:<line>`` references that
``curator.py show`` opens. Texts are redacted. The lenses of the review (references/lenses.md) read these keys.
Standard library only.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from _redact import redact
from _sources import EDIT_TOOLS, READ_TOOLS, SHELL_TOOLS, Session, cut

FIGURE_KEYS = (
    "sessions",
    "tools",
    "programs",
    "errors",
    "causes",
    "commands",
    "scripts",
    "sequences",
    "corrections",
    "skills",
    "subagents",
    "mcp",
    "context",
    "outputs",
    "rereads",
    "orientation",
    "usage",
)
TOP = 15  # entries of a ranked list
REFS = 5  # evidence references of one entry
BIG_OUTPUT = 20_000  # characters of a tool result that count as a big output
REREAD = 3  # reads of one file in one session that count as re-reading
ORIENTATION_CALLS = 15  # the first calls of a session, where an agent finds its way
MAX_SEGMENTS = 12  # segments of one command line looked at for programs
SUBCOMMANDS = frozenset(
    {
        "git",
        "gh",
        "docker",
        "kubectl",
        "npm",
        "pnpm",
        "yarn",
        "bun",
        "uv",
        "pip",
        "cargo",
        "go",
        "make",
        "just",
        "poetry",
        "brew",
        "terraform",
        "helm",
        "systemctl",
        "launchctl",
        "evo-agents",
        "evo",
        "claude",
        "codex",
        "npx",
    }
)
VALUED_OPTIONS = {
    "git": ("-C", "-c", "--git-dir", "--work-tree"),
    "docker": ("--context", "-H"),
    "uv": ("--directory",),
}
SKIPPED = frozenset({"cd", "pushd", "popd", "export", "source", ".", "set", "time", "env", "sudo", "nohup", "exec"})
TRIVIAL = frozenset(
    {"ls", "pwd", "echo", "cat", "head", "tail", "wc", "true", "sleep", "date", "clear", "which", "printf"}
)
# Programs that read and search: how an agent looks around, not a step a CLI would take over.
EXPLORE = frozenset(
    {
        "grep",
        "rg",
        "egrep",
        "sed",
        "awk",
        "find",
        "fd",
        "cut",
        "sort",
        "uniq",
        "tree",
        "less",
        "xargs",
        "tr",
        "stat",
        "file",
        "du",
        "nl",
        "column",
        "for",
        "while",
        "if",
        "test",
        "[",
    }
)
# Commands every change runs: worth counting as programs, not as candidates for a new command.
ROUTINE = frozenset(
    {
        "git status",
        "git diff",
        "git log",
        "git show",
        "git add",
        "git commit",
        "git branch",
        "git rev-parse",
        "git restore",
        "git stash",
    }
)
INLINE = re.compile(
    r"^(?:[A-Za-z_]\w*=\S*\s+)*((?:uv run\s+)?(?:python3?|node|ruby|perl|bash|sh|zsh|deno|bun))\b[^\n|;&]*?"
    r"(?:<<-?\s*['\"]?(\w+)['\"]?|\s-c\s+|\s-e\s+)"
)
SCRIPT_TARGET = re.compile(
    r"""['"]((?:[~./\w@-]+/)*[\w@.-]+\.(?:ya?ml|json|jsonl|md|toml|csv|txt|py|sqlite|db|log|html))['"]"""
)
BASIC_MODULES = frozenset(
    {
        "json",
        "sys",
        "os",
        "re",
        "pathlib",
        "collections",
        "subprocess",
        "time",
        "datetime",
        "glob",
        "itertools",
        "functools",
        "typing",
        "textwrap",
        "shutil",
        "math",
        "__future__",
    }
)
CONTINUE = re.compile(
    r"^\s*(?:continue|go on|go ahead|keep going|tiếp|tiếp tục|tiếp đi|làm tiếp|ok|okay|yes|tiep)\W*$", re.I
)
SEGMENT = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# The causes of a failed tool result, tried in order; the first that matches wins.
CAUSES: tuple[tuple[str, re.Pattern], ...] = (
    (
        "denied",
        re.compile(
            r"doesn't want to proceed|user (?:rejected|denied|declined)|permission to use \S+ (?:was )?denied"
            r"|tool use was rejected",
            re.I,
        ),
    ),
    (
        "harness_blocked",
        re.compile(
            r"\bblocked\b|\bwas denied\b|\bdenied by\b|\bhook\b[^.\n]{0,60}\b(?:blocked|denied|refused)\b"
            r"|\bnot allowed\b|\brequires approval\b",
            re.I,
        ),
    ),
    (
        "server_5xx",
        re.compile(
            r"\b(?:HTTP|status|answered|returned|got)\s*:?\s*5\d\d\b|\b50[0-4]\s+(?:Internal|Bad Gateway|Service "
            r"Unavailable|Gateway Time)",
            re.I,
        ),
    ),
    ("rate_limit", re.compile(r"rate.?limit|too many requests|\b429\b|\boverloaded\b", re.I)),
    (
        "network",
        re.compile(
            r"connection (?:refused|reset|timed out|closed)|could not resolve|name or service not known|temporary "
            r"failure in name resolution|network is unreachable|\bunreachable\b|\bECONN\w+|timed out",
            re.I,
        ),
    ),
    ("credentials", re.compile(r"\b401\b|unauthori[sz]ed|authentication failed|invalid token|token expired", re.I)),
    ("os_permission", re.compile(r"permission denied|operation not permitted|\bEACCES\b|\bEPERM\b", re.I)),
    (
        "missing_tool",
        re.compile(r"command not found|not installed|ModuleNotFoundError|No module named|executable file not found"),
    ),
    (
        "wrong_input",
        re.compile(
            r"InputValidationError|has not been read yet|String to replace not found|Found \d+ matches of the string"
            r"|File does not exist|No such file or directory|is a directory|unknown (?:option|flag|command)"
            r"|unrecognized (?:option|arguments)|invalid (?:option|argument|choice)|usage:",
            re.I,
        ),
    ),
    ("tests_failed", re.compile(r"\b\d+ failed\b|FAILED\b|AssertionError|Tests?:\s+\d+ failed", re.I)),
    (
        "lint_failed",
        re.compile(
            r"\b[A-Z]{1,3}\d{3,4}\b.*\S|would reformat|files? (?:would be )?reformatted|Found \d+ errors?\b"
            r"|\d+ problems? \(\d+ errors?|error TS\d+|ruff|eslint|mypy",
            re.I,
        ),
    ),
    ("nothing_to_commit", re.compile(r"nothing to commit|nothing added to commit|no changes added to commit", re.I)),
    ("script_error", re.compile(r"Traceback \(most recent call last\)|SyntaxError|ReferenceError|Uncaught", re.I)),
)
ENVIRONMENT = ("harness_blocked", "server_5xx", "rate_limit", "network", "credentials", "os_permission", "missing_tool")
NO_MATCH_PROGRAMS = frozenset({"grep", "rg", "egrep", "diff", "test", "[", "cmp", "pgrep"})
# A turn of the person that corrects the agent, in Vietnamese or English: how a correction starts, or a phrase in it.
CORRECTION_START = re.compile(
    r"^\s*(?:không|khong|đừng|dung lai|dừng|sai|lại|chưa|nhầm|no\b|nope\b|not\b|don'?t|do not|stop\b|wrong|again"
    r"|instead|why did you|why are you)",
    re.I,
)
CORRECTION_PHRASE = re.compile(
    r"sai rồi|không phải|nhầm rồi|tôi đã nói|đã bảo|tôi bảo|i (?:said|told you|asked)|that'?s (?:not|wrong)"
    r"|not what i|you (?:forgot|missed|ignored)|chứ không|đừng có",
    re.I,
)
UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
NUMBER = re.compile(r"(?<![\w.])\d{2,}(?![\w.])")
LONG_QUOTED = re.compile(r"""(["'])(?:(?!\1).){24,}\1""", re.S)
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?.*", re.S)


def percentiles(values: list[int]) -> dict:
    if not values:
        return {"n": 0}
    ordered = sorted(values)

    def at(q: float) -> int:
        return ordered[min(len(ordered) - 1, int(q * (len(ordered) - 1) + 0.5))]

    return {"n": len(ordered), "p50": at(0.5), "p90": at(0.9), "max": ordered[-1]}


def ref(session: Session, seq: int) -> str:
    return f"{session.key}:{seq}"


@lru_cache(maxsize=65536)
def programs(command: str) -> tuple[str, ...]:
    """The programs a shell command runs, segment by segment, with the subcommand of the tools that have one:
    ``cd x && git push origin`` gives ``("git push",)``. The body of a heredoc is not a command."""
    found = []
    for segment in SEGMENT.split(HEREDOC.sub("", command or ""))[:MAX_SEGMENTS]:
        words = [word.strip("'\"()") for word in segment.split()]
        while words and (ASSIGNMENT.match(words[0]) or words[0] in SKIPPED):
            if words[0] in SKIPPED:
                words = words[1:] if words[0] not in ("cd", "pushd", "source", ".") else []
            else:
                words = words[1:]
        if not words:
            continue
        name = words[0].rsplit("/", 1)[-1].strip()
        if not name or not re.match(r"^[\w.@+\[-]", name):
            continue
        rest = words[1:]
        if name in SUBCOMMANDS:
            skip = VALUED_OPTIONS.get(name, ())
            while rest and rest[0].startswith("-"):
                rest = rest[2:] if rest[0] in skip else rest[1:]
            if rest:
                name = f"{name} {rest[0]}"
        elif name in ("python", "python3") and len(rest) >= 2 and rest[0] == "-m":
            name = f"python -m {rest[1]}"
        found.append(name)
    return tuple(found)


@lru_cache(maxsize=65536)
def main_program(command: str) -> str | None:
    """The program a command is about: its first that is not trivial, else its first."""
    names = programs(command)
    for name in names:
        if name.split()[0] not in TRIVIAL:
            return name
    return names[0] if names else None


def normalize(command: str) -> str:
    """A command with what changes between runs taken out, so two runs of the same step compare equal."""
    text = (command or "").strip()
    text = HEREDOC.sub(lambda found: f"<<{found.group(1)} ...", text)
    text = re.sub(r"^(?:cd\s+\S+\s*(?:&&|;)\s*)+", "", text)
    text = text.replace(str(Path.home()), "~")
    text = UUID.sub("<id>", text)
    text = SHA.sub(lambda found: "<sha>" if re.search(r"\d", found.group(0)) else found.group(0), text)
    text = NUMBER.sub("<n>", text)
    text = LONG_QUOTED.sub(lambda found: found.group(1) + "..." + found.group(1), text)
    text = re.sub(r"\s+", " ", text)
    return cut(text, 200)


def inline_script(command: str, root: str | None = None) -> str | None:
    """What an inline script (a heredoc or ``-c`` program) works on, as a name runs of the same job share:
    ``python3 script on plans/active/*.yaml``; None when the command is not an inline script."""
    text = re.sub(r"^(?:cd\s+\S+\s*(?:&&|;)\s*)+", "", (command or "").strip())
    found = INLINE.match(text)
    if not found:
        return None
    program = found.group(1).split()[-1]
    body = text[found.end() :]
    if found.group(2):
        lines = body.split("\n")[1:]
        end = next((i for i, line in enumerate(lines) if line.strip() == found.group(2)), len(lines))
        body = "\n".join(lines[:end])
    else:
        body = body.strip().strip("'\"")
    targets = SCRIPT_TARGET.findall(body)
    if targets:
        path = targets[0].replace(str(Path.home()), "~")
        if root and path.startswith(root.rstrip("/") + "/"):
            path = path[len(root.rstrip("/")) + 1 :]
        if "/" in path:
            path = re.sub(r"[^/]+(\.\w+)$", r"*\1", path)
        return f"{program} script on {path}"
    modules = sorted({m for m in re.findall(r"^\s*(?:import|from)\s+(\w+)", body, re.M)} - BASIC_MODULES)
    if modules:
        return f"{program} script using {', '.join(modules[:3])}"
    return f"{program} inline script"


def cause(call) -> str:
    text = call.error or ""
    for name, pattern in CAUSES:
        if pattern.search(text):
            return name
    if call.tool in SHELL_TOOLS:
        program = (main_program(call.command or "") or "").split()[0:1]
        body = re.sub(r"^(?:Exit code|exit code)\s*-?\d+\s*", "", text.strip())
        if program and program[0] in NO_MATCH_PROGRAMS and len(body) <= 20:
            return "no_match"
    return "other"


def _signature(call) -> str:
    first = (call.error or "").strip().splitlines()[0:1]
    text = first[0] if first else ""
    if re.match(r"^exit code -?\d+$", text, re.I) and len((call.error or "").splitlines()) > 1:
        text += " | " + call.error.strip().splitlines()[1]
    text = text.replace(str(Path.home()), "~")
    text = re.sub(r"(?:/[\w.@+-]+)+", "<path>", text)
    text = NUMBER.sub("<n>", UUID.sub("<id>", text))
    return f"{call.tool}: {cut(text, 140)}"


def _ranked(rows: list[dict], key: str, top: int = TOP) -> list[dict]:
    return sorted(rows, key=lambda row: (-row[key], str(row.get("name", ""))))[:top]


def compute(sessions: list[Session], min_sessions: int = 3, root: str | None = None) -> dict:
    figures: dict = {}
    by_kind = Counter((s.runtime, s.kind) for s in sessions)
    figures["sessions"] = {
        "total": len(sessions),
        "by_runtime": {
            runtime: {kind: n for (r, kind), n in by_kind.items() if r == runtime}
            for runtime in sorted({s.runtime for s in sessions})
        },
        "first": min((s.started for s in sessions if s.started), default=None),
        "last": max((s.ended for s in sessions if s.ended), default=None),
        "calls": sum(len(s.calls) for s in sessions),
        "turns": sum(1 for s in sessions for t in s.turns if t.kind == "prompt"),
    }
    figures.update(_tools(sessions))
    figures.update(_commands(sessions, min_sessions, root))
    figures["corrections"] = _corrections(sessions)
    figures["skills"] = _skills(sessions)
    figures["subagents"] = _subagents(sessions)
    figures["mcp"] = _mcp(sessions)
    figures.update(_context(sessions, min_sessions))
    figures["usage"] = _usage(sessions)
    return figures


def _tools(sessions: list[Session]) -> dict:
    tools: dict[str, dict] = defaultdict(lambda: {"calls": 0, "failed": 0, "sessions": set(), "refs": []})
    progs: dict[str, dict] = defaultdict(lambda: {"calls": 0, "failed": 0, "sessions": set(), "refs": []})
    errors: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "sessions": set(), "refs": [], "sample": "", "cause": ""}
    )
    causes: dict[str, dict] = defaultdict(lambda: {"count": 0, "sessions": set(), "refs": [], "sample": ""})
    for session in sessions:
        for call in session.calls:
            row = tools[call.tool]
            row["calls"] += 1
            row["sessions"].add(session.key)
            program = main_program(call.command) if call.tool in SHELL_TOOLS and call.command else None
            if program:
                progs[program]["calls"] += 1
                progs[program]["sessions"].add(session.key)
            if not call.failed:
                continue
            why = cause(call)
            if why in ("no_match", "denied"):
                counted = causes[why]
                counted["count"] += 1
                counted["sessions"].add(session.key)
                if len(counted["refs"]) < REFS:
                    counted["refs"].append(ref(session, call.seq))
                continue
            row["failed"] += 1
            if len(row["refs"]) < REFS:
                row["refs"].append(ref(session, call.seq))
            if program:
                progs[program]["failed"] += 1
                if len(progs[program]["refs"]) < REFS:
                    progs[program]["refs"].append(ref(session, call.seq))
            signature = _signature(call)
            error = errors[signature]
            error["count"] += 1
            error["sessions"].add(session.key)
            error["cause"] = why
            if len(error["refs"]) < REFS:
                error["refs"].append(ref(session, call.seq))
            if not error["sample"]:
                shown = call.command if call.command else (call.path or "")
                error["sample"] = redact(cut(f"{shown}\n-> {call.error}" if shown else call.error or "", 500))
            counted = causes[why]
            counted["count"] += 1
            counted["sessions"].add(session.key)
            if len(counted["refs"]) < REFS:
                counted["refs"].append(ref(session, call.seq))
            if not counted["sample"]:
                counted["sample"] = redact(cut(call.error or "", 300))

    def rows(table: dict, extra=None) -> list[dict]:
        out = []
        for name, row in table.items():
            item = {"name": name, "calls": row["calls"], "failed": row["failed"], "sessions": len(row["sessions"])}
            item["rate"] = round(row["failed"] / row["calls"], 3) if row["calls"] else 0.0
            item["refs"] = row["refs"]
            out.append(item)
        return out

    tool_rows = rows(tools)
    error_rows = [
        {
            "name": name,
            "count": row["count"],
            "sessions": len(row["sessions"]),
            "cause": row["cause"],
            "refs": row["refs"],
            "sample": row["sample"],
        }
        for name, row in errors.items()
    ]
    cause_rows = [
        {
            "name": name,
            "count": row["count"],
            "sessions": len(row["sessions"]),
            "environment": name in ENVIRONMENT,
            "refs": row["refs"],
            "sample": row["sample"],
        }
        for name, row in causes.items()
    ]
    return {
        "tools": sorted(tool_rows, key=lambda row: (-row["failed"], -row["calls"]))[: TOP * 2],
        "programs": sorted(rows(progs), key=lambda row: (-row["failed"], -row["calls"]))[: TOP * 2],
        "errors": sorted(error_rows, key=lambda row: (-row["sessions"], -row["count"]))[:TOP],
        "causes": _ranked(cause_rows, "count", top=len(cause_rows)),
    }


def _commands(sessions: list[Session], min_sessions: int, root: str | None = None) -> dict:
    seen: dict[str, dict] = defaultdict(lambda: {"count": 0, "sessions": set(), "refs": [], "example": "", "failed": 0})
    scripts: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "sessions": set(), "refs": [], "example": "", "failed": 0}
    )
    grams: dict[tuple, dict] = defaultdict(lambda: {"count": 0, "sessions": set(), "refs": []})
    for session in sessions:
        chain: list[tuple[str, int]] = []
        for call in session.calls:
            if call.tool not in SHELL_TOOLS or not call.command:
                continue
            program = main_program(call.command)
            if not program or program.split()[0] in TRIVIAL:
                continue
            script = inline_script(call.command, root)
            if program.split()[0] in EXPLORE or program in ROUTINE:
                key, table = None, None
            elif script:
                key, table = script, scripts
            else:
                key, table = normalize(call.command), seen
            if key is None:
                continue
            row = table[key]
            row["count"] += 1
            row["failed"] += 1 if call.failed else 0
            row["sessions"].add(session.key)
            if len(row["refs"]) < REFS:
                row["refs"].append(ref(session, call.seq))
            if not row["example"]:
                row["example"] = redact(cut(call.command, 400))
            if not script and (not chain or chain[-1][0] != program):
                chain.append((program, call.seq))
        for size in (3, 4):
            for start in range(len(chain) - size + 1):
                window = chain[start : start + size]
                steps = tuple(name for name, _ in window)
                if len(set(steps)) < 2:
                    continue
                row = grams[steps]
                row["count"] += 1
                if session.key not in row["sessions"]:
                    row["sessions"].add(session.key)
                    if len(row["refs"]) < REFS:
                        row["refs"].append(ref(session, window[0][1]))

    def repeated(table: dict) -> list[dict]:
        rows = [
            {
                "name": key,
                "count": row["count"],
                "sessions": len(row["sessions"]),
                "failed": row["failed"],
                "refs": row["refs"],
                "example": row["example"],
            }
            for key, row in table.items()
            if len(row["sessions"]) >= min_sessions
        ]
        return sorted(rows, key=lambda row: (-row["sessions"], -row["count"]))[: TOP + 10]

    kept = {steps: row for steps, row in grams.items() if len(row["sessions"]) >= min_sessions}
    # A sequence inside a longer one that ran in as many sessions says nothing the longer one does not.
    maximal = []
    for steps, row in kept.items():
        longer = [
            other
            for other in kept
            if len(other) > len(steps)
            and any(other[i : i + len(steps)] == steps for i in range(len(other) - len(steps) + 1))
            and len(kept[other]["sessions"]) >= len(row["sessions"])
        ]
        if not longer:
            maximal.append(
                {
                    "name": " -> ".join(steps),
                    "sessions": len(row["sessions"]),
                    "count": row["count"],
                    "refs": row["refs"],
                }
            )
    return {
        "commands": repeated(seen),
        "scripts": repeated(scripts),
        "sequences": _ranked(maximal, "sessions"),
    }


def _corrections(sessions: list[Session]) -> dict:
    found = []
    interrupts = []
    prompts = 0
    for session in sessions:
        if session.kind != "interactive":
            continue
        after_interrupt = False
        for turn in session.turns:
            if turn.kind == "interrupt":
                after_interrupt = True
                if len(interrupts) < TOP:
                    interrupts.append(ref(session, turn.seq))
                continue
            if turn.kind != "prompt":
                after_interrupt = False
                continue
            prompts += 1
            text = turn.text
            why = None
            if CORRECTION_START.search(text):
                why = "starts"
            elif CORRECTION_PHRASE.search(text):
                why = "phrase"
            elif after_interrupt and not CONTINUE.match(text):
                why = "after_interrupt"
            after_interrupt = False
            if why:
                found.append({"ref": ref(session, turn.seq), "why": why, "text": redact(cut(text, 300))})
    return {
        "prompts": prompts,
        "count": len(found),
        "interrupts": len(interrupts),
        "interrupt_refs": interrupts,
        "turns": found[: TOP * 3],
        "note": "matched by words, not read: check each before counting it as a correction",
    }


def _skills(sessions: list[Session]) -> list[dict]:
    rows: dict[str, dict] = defaultdict(lambda: {"loads": 0, "sessions": set(), "via": Counter(), "refs": []})
    for session in sessions:
        for call in session.calls:
            if call.skill:
                via = "skill_tool" if call.tool == "Skill" else "read"
                row = rows[call.skill]
                row["loads"] += 1
                row["via"][via] += 1
                row["sessions"].add(session.key)
                if len(row["refs"]) < REFS:
                    row["refs"].append(ref(session, call.seq))
        for turn in session.turns:
            if turn.kind == "command":
                name = turn.text.split()[0]
                row = rows[name]
                row["loads"] += 1
                row["via"]["slash"] += 1
                row["sessions"].add(session.key)
                if len(row["refs"]) < REFS:
                    row["refs"].append(ref(session, turn.seq))
        for name in session.attributed_skills:
            rows[name]["sessions"].add(session.key)
            rows[name]["via"]["attributed_sessions"] += 1
    out = [
        {
            "name": name,
            "loads": row["loads"],
            "sessions": len(row["sessions"]),
            "via": dict(row["via"]),
            "refs": row["refs"],
        }
        for name, row in rows.items()
    ]
    return sorted(out, key=lambda row: (-row["sessions"], -row["loads"], row["name"]))


def _subagents(sessions: list[Session]) -> dict:
    started: dict[str, dict] = defaultdict(lambda: {"calls": 0, "sessions": set()})
    for session in sessions:
        for call in session.calls:
            if call.subagent:
                started[call.subagent]["calls"] += 1
                started[call.subagent]["sessions"].add(session.key)
    runs = [s for s in sessions if s.kind == "subagent"]
    return {
        "started": sorted(
            ({"name": k, "calls": v["calls"], "sessions": len(v["sessions"])} for k, v in started.items()),
            key=lambda row: -row["calls"],
        ),
        "transcripts": len(runs),
        "calls": sum(len(s.calls) for s in runs),
        "by_type": dict(Counter(s.agent_type or "unknown" for s in runs).most_common(TOP)),
    }


def _mcp(sessions: list[Session]) -> list[dict]:
    servers: dict[str, dict] = defaultdict(lambda: {"calls": 0, "failed": 0, "sessions": set(), "tools": Counter()})
    for session in sessions:
        for call in session.calls:
            if call.tool.startswith("mcp__"):
                parts = call.tool.split("__")
                server = parts[1] if len(parts) > 2 else call.tool
                row = servers[server]
                row["calls"] += 1
                row["failed"] += 1 if call.failed else 0
                row["sessions"].add(session.key)
                row["tools"][parts[-1]] += 1
    newest = _newest(sessions, lambda s: s.runtime == "claude" and (s.mcp_servers or s.deferred_tools))
    if newest:
        for name in newest.mcp_servers:
            servers[_server_key(name)]  # an instructed server with no call still shows, with 0 calls
        for name in newest.deferred_tools:
            parts = name.split("__")
            if name.startswith("mcp__") and len(parts) > 2:
                servers[parts[1]]
    out = []
    for name, row in servers.items():
        item = {"name": name, "calls": row["calls"], "failed": row["failed"], "sessions": len(row["sessions"])}
        item["tools"] = dict(row["tools"].most_common(8))
        if newest:
            item["instruction_chars"] = sum(
                size for server, size in newest.mcp_servers.items() if _server_key(server) == name
            )
            item["deferred_tools"] = sum(1 for tool in newest.deferred_tools if tool.startswith(f"mcp__{name}__"))
        out.append(item)
    return sorted(out, key=lambda row: (-row["calls"], row["name"]))


def _server_key(name: str) -> str:
    """The server part of an MCP tool name for a server as the instructions name it: ``plugin:evo-hub:evo-hub`` is
    ``plugin_evo-hub_evo-hub``."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)


def _newest(sessions: list[Session], keep) -> Session | None:
    chosen = [s for s in sessions if s.kind == "interactive" and keep(s)]
    return max(chosen, key=lambda s: s.ended or "", default=None)


def _context(sessions: list[Session], min_sessions: int) -> dict:
    context: dict = {"startup_tokens": {}, "peak_tokens": {}, "compactions": {}, "loaded": {}}
    for runtime in sorted({s.runtime for s in sessions}):
        mine = [s for s in sessions if s.runtime == runtime]
        for kind in ("interactive", "headless", "subagent"):
            group = [s for s in mine if s.kind == kind and s.context]
            if not group:
                continue
            label = f"{runtime}:{kind}"
            context["startup_tokens"][label] = percentiles([s.context[0] for s in group])
            context["peak_tokens"][label] = percentiles([max(s.context) for s in group])
            compacted = [s for s in group if s.compactions]
            context["compactions"][label] = {
                "sessions": len(compacted),
                "of": len(group),
                "total": sum(len(s.compactions) for s in compacted),
                "refs": [ref(s, s.compactions[0]) for s in compacted[:REFS]],
            }
    newest = _newest(sessions, lambda s: s.runtime == "claude" and s.loaded)
    if newest:
        context["loaded"] = {
            "session": newest.key,
            "at": newest.ended,
            "startup_tokens": newest.context[0] if newest.context else None,
            "chars": dict(sorted(newest.loaded.items(), key=lambda item: -item[1])),
            "note": "characters the runtime put into the context at the start; about 4 per token in English, "
            "fewer for code and for text with diacritics",
        }
    outputs: dict[str, dict] = defaultdict(lambda: {"calls": 0, "chars": [], "persisted": 0})
    big = []
    reads: dict[str, dict] = defaultdict(lambda: {"sessions": set(), "reads": 0, "chars": 0})
    rereads = []
    orientation: dict[str, set] = defaultdict(set)
    for session in sessions:
        per_file: Counter = Counter()
        first_seq: dict[str, int] = {}
        for index, call in enumerate(session.calls):
            name = call.tool
            if call.tool in SHELL_TOOLS and call.command:
                name = f"{call.tool}: {main_program(call.command) or '?'}"
            row = outputs[name]
            row["calls"] += 1
            row["chars"].append(call.output_chars)
            row["persisted"] += 1 if call.persisted else 0
            if call.output_chars >= BIG_OUTPUT or call.persisted:
                shown = normalize(call.command) if call.command else (call.path or "")
                big.append(
                    {
                        "ref": ref(session, call.seq),
                        "tool": name,
                        "chars": call.output_chars,
                        "persisted": call.persisted,
                        "what": redact(cut(shown, 200)),
                    }
                )
            path = call.path if (call.tool in READ_TOOLS or (call.tool in SHELL_TOOLS and call.path)) else None
            if path and call.tool not in EDIT_TOOLS:
                path = path.replace(str(Path.home()), "~")
                per_file[path] += 1
                first_seq.setdefault(path, call.seq)
                reads[path]["sessions"].add(session.key)
                reads[path]["reads"] += 1
                reads[path]["chars"] += call.output_chars
                if index < ORIENTATION_CALLS and session.kind == "interactive":
                    orientation[path].add(session.key)
        for path, count in per_file.items():
            if count >= REREAD:
                rereads.append({"name": path, "reads": count, "ref": ref(session, first_seq[path])})
    output_rows = []
    for name, row in outputs.items():
        stats = percentiles(row["chars"])
        output_rows.append(
            {
                "name": name,
                "calls": row["calls"],
                "chars_total": sum(row["chars"]),
                "chars_p90": stats.get("p90", 0),
                "persisted": row["persisted"],
            }
        )
    return {
        "context": context,
        "outputs": {
            "by_tool": sorted(output_rows, key=lambda row: -row["chars_total"])[:TOP],
            "big": sorted(big, key=lambda row: -row["chars"])[:TOP],
            "big_count": len(big),
            "threshold_chars": BIG_OUTPUT,
        },
        "rereads": {
            "within_session": sorted(rereads, key=lambda row: -row["reads"])[:TOP],
            "across_sessions": sorted(
                (
                    {"name": p, "sessions": len(r["sessions"]), "reads": r["reads"], "chars": r["chars"]}
                    for p, r in reads.items()
                    if len(r["sessions"]) >= min_sessions
                ),
                key=lambda row: (-row["sessions"], -row["chars"]),
            )[:TOP],
        },
        "orientation": sorted(
            ({"name": p, "sessions": len(keys)} for p, keys in orientation.items() if len(keys) >= min_sessions),
            key=lambda row: -row["sessions"],
        )[:TOP],
    }


def _usage(sessions: list[Session]) -> dict:
    usage: dict = {}
    for runtime in sorted({s.runtime for s in sessions}):
        mine = [s for s in sessions if s.runtime == runtime]
        total: Counter = Counter()
        models: Counter = Counter()
        for session in mine:
            total.update(session.usage)
            models.update(session.models)
        usage[runtime] = {
            "tokens": dict(total),
            "models": dict(models.most_common(8)),
            "api_errors": sum(s.api_errors for s in mine),
        }
    return usage
