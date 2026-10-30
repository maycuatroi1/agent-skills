#!/usr/bin/env python3
"""curator: review the recent sessions of a harness and turn what they show into proposals with evidence.

The deterministic half of the curator skill. It reads the transcripts that Claude Code and Codex keep on this
machine for the sessions of one harness, counts what happened (tool errors and their causes, repeated commands and
command sequences, corrections, skills used, what filled the context), measures what every session loads before
anyone types, and writes a short report the agent reads instead of the transcripts. The agent then opens the
evidence it needs (``show``), writes proposals (``propose``), and records what the person decided (``decide``); a
later review measures whether an applied proposal moved its metric (``outcomes``).

    curator.py scope                 which directories and transcripts belong to this harness
    curator.py collect [--days 14]   figures, context inventory and report.md, in the state directory
    curator.py report                report.md again from the saved figures
    curator.py show REF              one piece of evidence: claude:<session>:<line>, codex:..., code:<path>:<line>
    curator.py propose --file F      check a proposal's evidence and file it
    curator.py list [--state open]   proposals
    curator.py decide ID ACTION      accept | reject | defer | applied | reverted, with --note and --commit
    curator.py outcomes              each applied proposal's metric, then and now
    curator.py backup FILE           copy a file into the state before changing it outside a repo
    curator.py notice                one line for a SessionStart hook when a review is due, else nothing

State lives outside the repo (``$CURATOR_STATE``, else ``$XDG_STATE_HOME/curator``, else ``~/.local/state/curator``),
one directory per harness: the figures quote what people typed and what commands printed, and must not reach git.
Python 3.9 or later, standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _context import inventory, tokens_estimate  # noqa: E402
from _figures import compute  # noqa: E402
from _redact import redact  # noqa: E402
from _sources import (  # noqa: E402
    RUNTIMES,
    cut,
    encode_path,
    find_claude,
    find_codex,
    in_scope,
    line_at,
    load,
)

VERSION = "0.2.0"
DEFAULT_DAYS = 14
DEFAULT_MIN_SESSIONS = 3
NOTICE_SESSIONS = 10
REJECTED_DAYS = 30  # a proposal like one rejected this recently is refused
LENSES = ("context", "cli", "skills", "tool_errors", "environment", "corrections", "harness", "cost")
KINDS = ("context", "cli", "skill", "rule", "memory", "hook", "permission", "harness", "docs")
STATES = ("open", "accepted", "rejected", "deferred", "applied", "reverted")
ACTIONS = {
    "accept": "accepted",
    "reject": "rejected",
    "defer": "deferred",
    "applied": "applied",
    "reverted": "reverted",
}
REQUIRED = ("title", "lens", "kind", "target", "evidence")
# The guard ladder, strongest first: remove the wrong path, a type or schema, a lint or runtime guard, a behaviour
# test, and prose (a rule, context, a document) last. A proposal names its rung; below the top it says why not higher.
LADDER = ("remove", "type", "lint", "test", "prose")
PROSE_KINDS = ("rule", "docs", "memory", "context")
WHY_NOT_HIGHER = re.compile(r"^##\s+Why not higher\s*$\n+(?=\S)(?!##)", re.M)
FAILING = ("failing_ref", "failing_input", "failing_probe")
RUN_REF = re.compile(r"^run:(\d+):(\d+)$")
REF = re.compile(r"^(claude|codex):([^:]+)(?::(\d+))?$")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fail(message: str, code: int = 1):
    print(f"curator: {message}", file=sys.stderr)
    sys.exit(code)


# Scope


def git(*args: str, cwd: Path | None = None) -> str | None:
    try:
        done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def find_root(given: str | None) -> Path:
    """The harness root: ``given``, else the main worktree of the git repo around the current directory, so every
    worktree of a harness shares one state."""
    if given:
        return Path(os.path.realpath(Path(given).expanduser()))
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir")
    if common and Path(common).name == ".git":
        return Path(common).parent.resolve()
    top = git("rev-parse", "--show-toplevel")
    return Path(top).resolve() if top else Path.cwd().resolve()


def worktrees(repo: Path) -> list[str]:
    listed = git("worktree", "list", "--porcelain", cwd=repo) if repo.is_dir() else None
    return [line[len("worktree ") :] for line in (listed or "").splitlines() if line.startswith("worktree ")]


def cluster_repos(root: Path) -> list[str]:
    """The repo paths a harness.yaml at ``root`` lists, if there is one."""
    manifest = root / "harness.yaml"
    if not manifest.is_file():
        return []
    text = manifest.read_text(encoding="utf-8", errors="replace")
    try:
        import yaml  # optional

        data = yaml.safe_load(text) or {}
        paths = [
            str(repo.get("path")) for repo in data.get("repos") or [] if isinstance(repo, dict) and repo.get("path")
        ]
    except Exception:
        section = text.split("\nrepos:", 1)[1] if "\nrepos:" in text else ""
        paths = [found.strip().strip("'\"") for found in re.findall(r"^\s*-?\s*path:\s*(.+)$", section, re.M)]
    return [str(Path(path).expanduser()) for path in paths]


def scope_paths(root: Path, cluster: bool, extra: list[str]) -> list[str]:
    paths = [str(root)]
    repos = [root]
    if cluster:
        repos += [Path(path) for path in cluster_repos(root)]
    repos += [Path(path).expanduser().resolve() for path in extra]
    for repo in repos:
        for path in [str(repo), *worktrees(repo)]:
            # A runtime records the directory it was started in, which may be a symlinked form of the real path
            # (/tmp and /private/tmp on macOS): keep both forms.
            for form in (os.path.abspath(path), os.path.realpath(path)):
                if form not in paths:
                    paths.append(form)
    return paths


def state_dir(root: Path) -> Path:
    base = os.environ.get("CURATOR_STATE")
    if base:
        folder = Path(base).expanduser()
    else:
        xdg = os.environ.get("XDG_STATE_HOME")
        folder = (Path(xdg).expanduser() if xdg else Path("~/.local/state").expanduser()) / "curator"
    folder = folder / encode_path(os.path.realpath(root))
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_json(path: Path, value) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


# Collect


def backlog(root: Path, state: Path) -> dict:
    def count(pattern: str) -> int:
        return len(list(root.glob(pattern)))

    return {
        "learned_skills_pending": count(".claude/skills/.learned/_pending/*/"),
        "cli_suggestions_pending": count(".claude/cli-suggestions/_pending/*"),
        "garden_proposals_pending": count("proposals/_pending/*.md"),
        "curator_open": sum(1 for p in proposals(state) if p.get("state") in ("open", "deferred")),
    }


def collect(args) -> None:
    root = find_root(args.root)
    paths = scope_paths(root, args.cluster, args.path or [])
    since = time.time() - args.days * 86400
    runtimes = tuple(args.runtime.split(",")) if args.runtime else RUNTIMES
    sessions, skipped = load(paths, since, runtimes, imported=args.include_imported)
    state = state_dir(root)
    figures = compute(sessions, min_sessions=args.min_sessions, root=str(root))
    newest = max(
        (s for s in sessions if s.runtime == "claude" and s.kind == "interactive" and s.skill_listing),
        key=lambda s: s.ended or "",
        default=None,
    )
    context = inventory(root, newest.skill_listing if newest else None, figures, bases=cluster_repos(root))
    meta = {
        "version": VERSION,
        "generated_at": now_iso(),
        "root": str(root),
        "paths": paths,
        "days": args.days,
        "runtimes": list(runtimes),
        "min_sessions": args.min_sessions,
        "skipped": dict(skipped),
        "backlog": backlog(root, state),
    }
    figures = {"meta": meta, **figures}
    index = {
        s.key: {
            "path": s.path,
            "kind": s.kind,
            "cwd": s.cwd,
            "started": s.started,
            "ended": s.ended,
            "lines": s.lines,
            "parent": s.parent,
        }
        for s in sessions
    }
    write_json(state / "figures.json", figures)
    write_json(state / "context.json", context)
    write_json(state / "index.json", index)
    report = render(figures, context, proposals(state))
    (state / "report.md").write_text(report, encoding="utf-8")
    if args.json:
        print(json.dumps({"state": str(state), "sessions": figures["sessions"], "skipped": dict(skipped)}))
        return
    by = figures["sessions"]["by_runtime"]
    shown = "; ".join(f"{rt} " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())) for rt, kinds in by.items())
    print(f"curator {VERSION}: {figures['sessions']['total']} sessions in {args.days} days ({shown or 'none'})")
    if skipped:
        print("skipped: " + ", ".join(f"{n} {why}" for why, n in sorted(skipped.items())))
    print(f"scope: {len(paths)} directories under {root}")
    print(f"report: {state / 'report.md'} ({len(report.splitlines())} lines)")
    print(f"figures: {state / 'figures.json'}, context: {state / 'context.json'}")


# The report


def short(reference: str) -> str:
    """A reference with each session id cut to 8 characters; ``show`` and ``propose`` resolve the prefix."""
    found = REF.match(reference)
    if not found:
        return reference
    runtime, ident, seq = found.groups()
    parts = [part.removeprefix("agent-")[:8] for part in ident.split("/")]
    return f"{runtime}:{'/'.join(parts)}" + (f":{seq}" if seq else "")


def refs(rows_refs: list[str], limit: int = 3) -> str:
    return ", ".join(short(r) for r in rows_refs[:limit])


def k(value) -> str:
    """A count as people read it: 870, 51.0k, 22.0M, 6.2B."""
    if not isinstance(value, (int, float)):
        return str(value)
    for size, unit in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if value >= size:
            return f"{value / size:.1f}{unit}"
    return str(value)


def render(figures: dict, context: dict, open_proposals: list[dict]) -> str:
    meta = figures["meta"]
    out = [f"# Curator report: {meta['root']}", ""]
    s = figures["sessions"]
    by = "; ".join(
        f"{rt}: " + ", ".join(f"{n} {kind}" for kind, n in sorted(kinds.items()))
        for rt, kinds in s["by_runtime"].items()
    )
    out.append(
        f"Window {meta['days']} days, {s['first'] or '-'} to {s['last'] or '-'}. Sessions {s['total']} ({by}). "
        f"Tool calls {s['calls']}, prompts {s['turns']}. Generated {meta['generated_at']}."
    )
    if meta["skipped"]:
        out.append("Skipped: " + ", ".join(f"{n} {why}" for why, n in sorted(meta["skipped"].items())) + ".")
    out.append(
        "References: `curator.py show <ref>`; ids are prefixes. Counts are deterministic; whether a signal "
        "matters is for the review to judge from the evidence."
    )

    ctx = figures["context"]
    out += ["", "## Context", ""]
    for label, stats in ctx["startup_tokens"].items():
        peak = ctx["peak_tokens"].get(label, {})
        comp = ctx["compactions"].get(label, {})
        out.append(
            f"- {label}: startup tokens p50 {k(stats.get('p50'))}, p90 {k(stats.get('p90'))} (n={stats['n']}); "
            f"peak p50 {k(peak.get('p50'))}, max {k(peak.get('max'))}; compacted {comp.get('sessions', 0)} of "
            f"{comp.get('of', 0)} {refs(comp.get('refs', []), 2)}"
        )
    loaded = ctx.get("loaded") or {}
    if loaded.get("chars"):
        out.append(
            f"- Loaded at start of {short(loaded['session'])} ({k(loaded.get('startup_tokens'))} tokens), "
            "characters by component:"
        )
        for name, chars in list(loaded["chars"].items())[:10]:
            out.append(f"  - {name.replace(str(Path.home()), '~')}: {k(chars)} (~{k(tokens_estimate(chars))} tokens)")
        itemized = tokens_estimate(sum(loaded["chars"].values()))
        if loaded.get("startup_tokens") and loaded["startup_tokens"] > itemized:
            out.append(
                f"  - not itemized by the transcript: about {k(loaded['startup_tokens'] - itemized)} tokens "
                "(tool schemas are part of it)"
            )
    out.append("- Instruction files (always loaded):")
    for f in context["files"]:
        sm = f["smells"]
        notes = []
        if sm["dated_lines"]:
            notes.append(f"{sm['dated_lines']} dated lines at {sm['dated_at'][:4]}")
        if sm["long_paragraphs"]:
            notes.append(
                f"{len(sm['long_paragraphs'])} long paragraphs at {[p['line'] for p in sm['long_paragraphs'][:4]]}"
            )
        if sm["unresolved_paths"]:
            notes.append("unresolved " + ", ".join(f"`{u['path']}`:{u['line']}" for u in sm["unresolved_paths"][:4]))
        out.append(
            f"  - {f['path']} ({'+'.join(f['runtimes'])}, {f['scope']}): {f['lines']} lines, {k(f['chars'])} "
            f"chars, ~{k(f['tokens_est'])} tokens" + (f"; {'; '.join(notes)}" if notes else "")
        )
    if context["duplicates"]:
        out.append(
            f"- Lines held by two loaded files: {len(context['duplicates'])}, e.g. "
            + "; ".join(f"{d['at'][0]} = {d['at'][1]}" for d in context["duplicates"][:3])
        )
    sk = context["skills"]
    if sk["listed"]:
        out.append(
            f"- Skill listing: {sk['listed']} skills, {k(sk['listing_chars'])} chars (~{k(sk['listing_tokens_est'])} "
            f"tokens) by where: {', '.join(f'{w} {k(c)}' for w, c in sk['by_where'].items())}. Unused in the "
            f"window: {len(sk['unused'])} skills, {k(sk['unused_chars'])} chars: "
            + ", ".join(f"{u['name']} ({k(u['chars'])})" for u in sk["unused"][:12])
        )
        if sk["long"]:
            out.append(f"  - Lines over 500 chars: {', '.join(sk['long'][:12])}")
        if sk["overlapping_triggers"]:
            out.append(
                "  - Same trigger phrase in two skills: "
                + "; ".join(f'"{o["phrase"]}" ({", ".join(o["skills"])})' for o in sk["overlapping_triggers"][:5])
            )
    mcp = [m for m in figures["mcp"] if m.get("instruction_chars") or m.get("deferred_tools") or m["calls"]]
    if mcp:
        out.append(
            "- MCP servers (calls in window, instruction chars, deferred tools): "
            + "; ".join(
                f"{m['name']} {m['calls']}/{k(m.get('instruction_chars', 0))}/{m.get('deferred_tools', 0)}"
                for m in mcp[:12]
            )
        )
    outs = figures["outputs"]
    out.append(
        f"- Big outputs (>= {k(outs['threshold_chars'])} chars or spilled to a file): {outs['big_count']}. "
        "Most output by tool: "
        + "; ".join(f"{o['name']} {k(o['chars_total'])} in {o['calls']} calls" for o in outs["by_tool"][:6])
    )
    for big in outs["big"][:5]:
        out.append(f"  - {short(big['ref'])} {big['tool']} {k(big['chars'])}: `{big['what'][:120]}`")
    rr = figures["rereads"]
    if rr["within_session"]:
        out.append(
            "- Files read 3 or more times in one session: "
            + "; ".join(f"{r['name']} x{r['reads']} {short(r['ref'])}" for r in rr["within_session"][:6])
        )
    if figures["orientation"]:
        out.append(
            "- Read in the first calls of many sessions (orientation): "
            + "; ".join(f"{o['name']} ({o['sessions']})" for o in figures["orientation"][:8])
        )

    out += ["", "## Tool errors", ""]
    for t in [t for t in figures["tools"] if t["failed"]][:10]:
        out.append(
            f"- {t['name']}: {t['failed']} of {t['calls']} failed ({t['rate']:.1%}) in {t['sessions']} sessions "
            f"{refs(t['refs'])}"
        )
    progs = [p for p in figures["programs"] if p["failed"]][:10]
    if progs:
        out.append("- Shell programs: " + "; ".join(f"{p['name']} {p['failed']}/{p['calls']}" for p in progs))
    out.append("- Repeated errors (signature, count, sessions, cause):")
    for e in figures["errors"][:10]:
        out.append(f"  - `{e['name'][:150]}` x{e['count']} in {e['sessions']} [{e['cause']}] {refs(e['refs'])}")

    out += ["", "## Causes and environment", ""]
    for c in figures["causes"]:
        flag = " (environment)" if c.get("environment") else ""
        out.append(f"- {c['name']}{flag}: {c['count']} in {c['sessions']} sessions {refs(c['refs'])}")

    cor = figures["corrections"]
    out += [
        "",
        "## Corrections",
        "",
        f"{cor['count']} of {cor['prompts']} prompts match a correction pattern, {cor['interrupts']} interrupts. "
        f"{cor['note']}.",
    ]
    for turn in cor["turns"][:12]:
        out.append(f"- {short(turn['ref'])} [{turn['why']}] {turn['text'][:200]!r}")

    out += ["", "## Repeated commands and sequences (CLI candidates)", ""]
    for c in figures["commands"][:12]:
        out.append(
            f"- {c['sessions']} sessions, {c['count']} runs, {c['failed']} failed: `{c['name'][:160]}` "
            f"{refs(c['refs'], 2)}"
        )
    if figures.get("scripts"):
        out.append("- Inline scripts (heredoc or -c), by what they work on:")
        for c in figures["scripts"][:8]:
            out.append(
                f"  - {c['sessions']} sessions, {c['count']} runs, {c['failed']} failed: {c['name'][:120]} "
                f"{refs(c['refs'], 2)}"
            )
    if figures["sequences"]:
        out.append("- Sequences of programs repeated across sessions:")
        for seq in figures["sequences"][:8]:
            out.append(f"  - {seq['name']} ({seq['sessions']} sessions) {refs(seq['refs'], 2)}")

    out += ["", "## Skills and subagents", ""]
    used = figures["skills"][:15]
    if used:
        out.append("- Used: " + "; ".join(f"{u['name']} {u['sessions']}s/{u['loads']}" for u in used))
    sub = figures["subagents"]
    if sub["started"]:
        out.append(
            "- Subagents started: "
            + "; ".join(f"{a['name']} {a['calls']}" for a in sub["started"][:8])
            + f"; {sub['transcripts']} subagent transcripts, {sub['calls']} calls in them"
        )
    b = meta["backlog"]
    out.append(
        f"- Backlog: {b['learned_skills_pending']} learned skills pending, {b['cli_suggestions_pending']} CLI "
        f"suggestions pending, {b['garden_proposals_pending']} garden proposals pending, "
        f"{b['curator_open']} curator proposals open or deferred"
    )
    st = context["settings"]
    if st["hooks"]:
        out.append("- Hooks: " + "; ".join(f"{h['event']}: {h['command'][:70]}" for h in st["hooks"][:8]))
    mem = context["memory"]
    if mem["files"] or mem["index_lines"]:
        out.append(
            f"- Memory: {mem['files']} files, index {mem['index_lines']} lines; missing targets "
            f"{mem['missing_targets'][:3]}, not indexed {mem['unindexed'][:3]}"
        )

    out += ["", "## Usage", ""]
    for runtime, u in figures["usage"].items():
        tokens = ", ".join(f"{name} {k(v)}" for name, v in u["tokens"].items())
        out.append(f"- {runtime}: {tokens}; models {u['models']}; API errors {u['api_errors']}")

    if open_proposals:
        out += ["", "## Proposals open or deferred", ""]
        for p in open_proposals:
            if p.get("state") in ("open", "deferred"):
                out.append(f"- {p['id']} [{p.get('state')}] {p.get('kind')}: {p.get('title')} -> {p.get('target')}")
    return "\n".join(out) + "\n"


def report(args) -> None:
    root = find_root(args.root)
    state = state_dir(root)
    figures = read_json(state / "figures.json")
    context = read_json(state / "context.json")
    if not figures or not context:
        fail("no figures yet: run `curator.py collect` first")
    text = render(figures, context, proposals(state))
    (state / "report.md").write_text(text, encoding="utf-8")
    print(text if args.print else str(state / "report.md"))


# Evidence


def resolve_session(index: dict, runtime: str, prefix: str) -> str | None:
    """The key of the one session of ``index`` whose id starts with ``prefix``, part by part."""
    parts = prefix.split("/")
    matches = []
    for key in index:
        rt, ident = key.split(":", 1)
        if rt != runtime:
            continue
        idparts = ident.split("/")
        if len(idparts) == len(parts) and all(
            a.startswith(b) or a.removeprefix("agent-").startswith(b) for a, b in zip(idparts, parts)
        ):
            matches.append(key)
    return matches[0] if len(matches) == 1 else None


def summarize(line: dict, limit: int = 1500) -> str:
    """One transcript line as text a person can read: what was said, called or returned."""
    pieces = []
    message = line.get("message") if isinstance(line.get("message"), dict) else None
    payload = line.get("payload") if isinstance(line.get("payload"), dict) else None
    if message is not None:
        content = message.get("content")
        if isinstance(content, str):
            pieces.append(content)
        for item in content if isinstance(content, list) else []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                pieces.append(str(item.get("text")))
            elif item.get("type") == "tool_use":
                pieces.append(f"[tool_use {item.get('name')}] {json.dumps(item.get('input'), ensure_ascii=False)}")
            elif item.get("type") == "tool_result":
                body = item.get("content")
                if isinstance(body, list):
                    body = "\n".join(str(b.get("text", "")) for b in body if isinstance(b, dict))
                pieces.append(f"[tool_result{' error' if item.get('is_error') else ''}] {body}")
    elif payload is not None:
        item = payload.get("item") if isinstance(payload.get("item"), dict) else None
        shown = item or payload
        keep = {key: value for key, value in shown.items() if key not in ("encrypted_content", "id")}
        pieces.append(json.dumps(keep, ensure_ascii=False))
    else:
        keep = {key: value for key, value in line.items() if key not in ("uuid", "parentUuid", "sessionId")}
        pieces.append(json.dumps(keep, ensure_ascii=False))
    kind = line.get("type") or "?"
    sub = line.get("subtype") or (payload or {}).get("type") or ""
    return f"[{kind}{'/' + sub if sub else ''} {line.get('timestamp', '')}] " + redact(cut("\n".join(pieces), limit))


def show(args) -> None:
    root = find_root(args.root)
    state = state_dir(root)
    reference = args.ref
    if reference.startswith("code:"):
        rest = reference[len("code:") :]
        found = re.match(r"^(.*?)(?::(\d+))?$", rest)
        path = Path(found.group(1)).expanduser()
        path = path if path.is_absolute() else root / path
        if not path.is_file():
            fail(f"no file {path}")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        line = int(found.group(2) or 1)
        lo, hi = max(1, line - args.around), min(len(lines), line + args.around)
        for number in range(lo, hi + 1):
            print(f"{number:>5}{'>' if number == line else ' '} {redact(lines[number - 1])}")
        return
    found = REF.match(reference)
    if not found:
        fail("a reference is claude:<session>[:<line>], codex:<session>[:<line>] or code:<path>[:<line>]")
    runtime, prefix, seq = found.groups()
    index = read_json(state / "index.json", {})
    key = resolve_session(index, runtime, prefix)
    if not key:
        fail(f"no single session of the last collect matches {runtime}:{prefix}")
    entry = index[key]
    if not seq:
        print(json.dumps({"session": key, **entry}, ensure_ascii=False, indent=1))
        return
    seq = int(seq)
    path = entry["path"]
    print(f"{key} line {seq} of {entry['lines']} ({entry['kind']}, {entry['cwd']})")
    for number in range(max(1, seq - args.around), seq + args.around + 1):
        line = line_at(path, number)
        if line is not None:
            limit = args.chars if number == seq else 300
            print(f"{'>' if number == seq else ' '}{number}: {summarize(line, limit)}")


# Proposals


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """``key: value`` lines and ``- item`` lists between two ``---`` lines, and the body after them."""
    if not text.startswith("---"):
        return {}, text
    head, sep, body = text[3:].partition("\n---")
    if not sep:
        return {}, text
    data: dict = {}
    current = None
    for raw in head.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", raw)
        if item and current:
            if not isinstance(data.get(current), list):
                data[current] = []
            data[current].append(item.group(1).strip().strip("'\""))
            continue
        pair = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", raw)
        if pair:
            current = pair.group(1)
            value = pair.group(2).strip()
            if value.startswith("[") and value.endswith("]"):
                data[current] = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
            else:
                data[current] = value.strip("'\"") if value else ""
    return data, body.lstrip("\n").removeprefix("---").lstrip("\n")


def dump_frontmatter(data: dict, body: str) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines += [f"  - {item}" for item in value]
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n---\n\n" + body.strip() + "\n"


def proposals(state: Path) -> list[dict]:
    folder = state / "proposals"
    out = []
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        data, _ = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        if data.get("id"):
            out.append(data)
    return out


def check_evidence(reference: str, index: dict, root: Path, figures: dict, context: dict) -> str | None:
    """Why ``reference`` cannot be found, or None when it can."""
    if reference.startswith("code:"):
        found = re.match(r"^code:(.*?)(?::(\d+))?$", reference)
        path = Path(found.group(1)).expanduser()
        path = path if path.is_absolute() else root / path
        if not path.is_file():
            return f"no file {path}"
        if found.group(2) and int(found.group(2)) > len(
            path.read_text(encoding="utf-8", errors="replace").splitlines()
        ):
            return f"{path} has fewer lines than {found.group(2)}"
        return None
    for prefix, value in (("figure:", figures), ("inventory:", context)):
        if reference.startswith(prefix):
            for part in reference[len(prefix) :].split("."):
                if isinstance(value, dict) and part in value:
                    value = value[part]
                elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
                    value = value[int(part)]
                else:
                    return f"nothing at {reference}"
            return None
    found = REF.match(reference)
    if not found:
        return "not a reference (claude:, codex:, code:, figure: or inventory:)"
    runtime, prefix, seq = found.groups()
    key = resolve_session(index, runtime, prefix)
    if not key:
        return "no single session of the last collect matches"
    if seq and int(seq) > int(index[key].get("lines") or 0):
        return f"session {key} has {index[key].get('lines')} lines"
    return None


def check_guard(data: dict, body: str) -> list[str]:
    """What is wrong with the rung of the guard ladder a proposal names; required for the failure lenses."""
    guard = data.get("guard")
    if not guard:
        if data.get("lens") in ("corrections", "tool_errors"):
            return [f"missing guard: one of {', '.join(LADDER)}, the highest rung that can work (references/building.md)"]
        return []
    if guard not in LADDER:
        return [f"guard is one of {', '.join(LADDER)}"]
    problems = []
    if guard == "prose" and data.get("kind") not in PROSE_KINDS:
        problems.append(f"guard prose is a change of kind {', '.join(PROSE_KINDS)}, not {data.get('kind')}")
    if guard != "prose" and data.get("kind") in PROSE_KINDS:
        problems.append(f"kind {data.get('kind')} is prose; set guard: prose or change the kind")
    if guard != LADDER[0] and not WHY_NOT_HIGHER.search(body):
        problems.append(f"guard {guard} is below {LADDER[0]}: add a '## Why not higher' section saying why each higher rung cannot work")
    return problems


def squash(text: str) -> str:
    return " ".join(str(text).split()).casefold()


def check_failing_example(data: dict, index: dict) -> list[str]:
    """What is missing from the failing example a proposal that cites a correction must carry: the concrete input
    of the time it went wrong, quoted from the transcript line or run event it cites, and the command or probe that
    shows it still goes wrong on the harness as it is. An example written for the proposal is refused."""
    if data.get("lens") != "corrections":
        return []
    problems = [f"missing {key} (a correction needs a real failing example)" for key in FAILING if not data.get(key)]
    if problems:
        return problems
    reference, quoted = str(data["failing_ref"]), squash(data["failing_input"])
    if len(quoted) < 8:
        return ["failing_input is shorter than 8 characters: quote the whole input that went wrong"]
    if RUN_REF.match(reference):
        return []  # a hub run's event: the reviewer reads it with `evo-agents hub run logs`
    found = REF.match(reference)
    if not found or not found.group(3):
        return [f"failing_ref {reference}: a transcript line (claude:<session>:<line>, codex:...) or run:<id>:<event>"]
    runtime, prefix, seq = found.groups()
    key = resolve_session(index, runtime, prefix)
    if not key:
        return [f"failing_ref {reference}: no single session of the last collect matches"]
    line = line_at(index[key]["path"], int(seq))
    if line is None:
        return [f"failing_ref {reference}: no such line"]
    if quoted not in squash(summarize(line, 10**7)) and quoted not in squash(redact(json.dumps(line, ensure_ascii=False))):
        return [f"failing_input is not in {reference}: quote the input from that line, do not write an example"]
    return []


def slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")[:48] or "proposal"


def ledger(state: Path, event: dict) -> None:
    with open(state / "ledger.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": now_iso(), **event}, ensure_ascii=False) + "\n")


def ledger_events(state: Path) -> list[dict]:
    path = state / "ledger.jsonl"
    events = []
    for raw in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
        try:
            events.append(json.loads(raw))
        except ValueError:
            continue
    return events


def propose(args) -> None:
    root = find_root(args.root)
    state = state_dir(root)
    source = Path(args.file).expanduser()
    if not source.is_file():
        fail(f"no file {source}")
    data, body = parse_frontmatter(source.read_text(encoding="utf-8"))
    problems = [f"missing {key}" for key in REQUIRED if not data.get(key)]
    if data.get("lens") and data["lens"] not in LENSES:
        problems.append(f"lens is one of {', '.join(LENSES)}")
    if data.get("kind") and data["kind"] not in KINDS:
        problems.append(f"kind is one of {', '.join(KINDS)}")
    evidence = data.get("evidence") or []
    if isinstance(evidence, str):
        evidence = [evidence]
    data["evidence"] = evidence
    index = read_json(state / "index.json", {})
    figures = read_json(state / "figures.json", {})
    context = read_json(state / "context.json", {})
    for reference in evidence:
        why = check_evidence(reference, index, root, figures, context)
        if why:
            problems.append(f"evidence {reference}: {why}")
    problems += check_guard(data, body)
    problems += check_failing_example(data, index)
    if data.get("metric"):
        value = metric(data["metric"], figures, context)
        if value is None:
            problems.append(f"metric {data['metric']}: cannot be measured (see references/proposals.md)")
        else:
            data["baseline"] = value
    if problems:
        fail("proposal refused:\n  " + "\n  ".join(problems))
    existing = proposals(state)
    same = [p for p in existing if p.get("kind") == data["kind"] and p.get("target") == data["target"]]
    if not args.force:
        for p in same:
            if p.get("state") in ("open", "accepted", "deferred"):
                fail(f"proposal {p['id']} already covers {data['kind']} of {data['target']} ({p['state']})")
            if p.get("state") == "rejected" and p.get("decided"):
                age = (
                    datetime.now(timezone.utc)
                    - datetime.strptime(p["decided"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                ).days
                if age < REJECTED_DAYS:
                    fail(
                        f"the person rejected {p['id']} for {data['kind']} of {data['target']} {age} days ago; "
                        "pass --force only with stronger evidence"
                    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    ident = f"{stamp}-{slug(data['title'])}"
    n = 2
    while (state / "proposals" / f"{ident}.md").exists():
        ident = f"{stamp}-{slug(data['title'])}-{n}"
        n += 1
    record = {"id": ident, "state": "open", "created": now_iso()}
    record.update({key: value for key, value in data.items() if key not in ("id", "state", "created")})
    record.update({key: redact(str(record[key])) for key in FAILING if record.get(key)})
    (state / "proposals").mkdir(exist_ok=True)
    (state / "proposals" / f"{ident}.md").write_text(dump_frontmatter(record, redact(body)), encoding="utf-8")
    ledger(
        state,
        {
            "id": ident,
            "event": "proposed",
            "kind": data["kind"],
            "target": data["target"],
            "metric": data.get("metric"),
            "value": data.get("baseline"),
        },
    )
    print(
        f"{ident} open ({data['lens']}, {data['kind']} -> {data['target']})"
        + (f", baseline {data['metric']} = {data['baseline']}" if data.get("metric") else "")
    )


def list_proposals(args) -> None:
    state = state_dir(find_root(args.root))
    rows = [p for p in proposals(state) if not args.state or p.get("state") == args.state]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    if not rows:
        print("no proposals" + (f" in state {args.state}" if args.state else ""))
    for p in rows:
        print(f"{p['id']} [{p.get('state')}] {p.get('lens')}/{p.get('kind')}: {p.get('title')} -> {p.get('target')}")


def decide(args) -> None:
    state = state_dir(find_root(args.root))
    path = state / "proposals" / f"{args.id}.md"
    if not path.is_file():
        fail(f"no proposal {args.id}")
    data, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    data["state"] = ACTIONS[args.action]
    data["decided"] = now_iso()
    if args.note:
        data["note"] = args.note.replace("\n", " ")
    if args.commit:
        data["commit"] = args.commit
    event = {"id": args.id, "event": data["state"], "note": args.note, "commit": args.commit}
    if args.action == "applied" and data.get("metric"):
        figures = read_json(state / "figures.json", {})
        context = read_json(state / "context.json", {})
        data["applied_value"] = metric(data["metric"], figures, context)
        data["applied_at"] = figures.get("meta", {}).get("generated_at", "")
        event["value"] = data["applied_value"]
    path.write_text(dump_frontmatter(data, body), encoding="utf-8")
    ledger(state, event)
    print(f"{args.id} {data['state']}")


# Metrics


def metric(name: str, figures: dict, context: dict):
    """The value of a named metric in a figures and context pair, or None when it cannot be read.
    references/proposals.md lists the names."""
    head, _, arg = name.partition(":")
    ctx = figures.get("context") or {}
    sessions = (figures.get("sessions") or {}).get("total") or 0
    label = arg or "claude:interactive"
    if head in ("startup_tokens", "peak_tokens"):
        return (ctx.get(head) or {}).get(label, {}).get("p50")
    if head == "compactions":
        row = (ctx.get("compactions") or {}).get(label)
        return round(row["sessions"] / row["of"], 3) if row and row.get("of") else None
    if head in ("tool_rate", "program_rate"):
        rows = figures.get("tools" if head == "tool_rate" else "programs") or []
        row = next((r for r in rows if r["name"] == arg), None)
        return row["rate"] if row else 0.0
    if head == "cause":
        row = next((r for r in figures.get("causes") or [] if r["name"] == arg), None)
        return round((row["count"] if row else 0) * 100 / sessions, 2) if sessions else None
    if head == "command":
        hit = sum(r["sessions"] for r in figures.get("commands") or [] if arg in r["name"])
        return round(hit / sessions, 3) if sessions else None
    if head == "file_chars":
        row = next((f for f in context.get("files") or [] if f["path"].endswith(arg)), None)
        return row["chars"] if row else None
    if head == "listing_chars":
        return (context.get("skills") or {}).get("listing_chars")
    if head == "skill":
        row = next((r for r in figures.get("skills") or [] if r["name"] == arg or r["name"].endswith(":" + arg)), None)
        return row["sessions"] if row else 0
    if head == "corrections":
        cor = figures.get("corrections") or {}
        return round(cor["count"] / cor["prompts"], 3) if cor.get("prompts") else None
    if head == "big_outputs":
        calls = (figures.get("sessions") or {}).get("calls") or 0
        return round((figures.get("outputs") or {}).get("big_count", 0) * 100 / calls, 2) if calls else None
    if head == "rereads":
        rows = (figures.get("rereads") or {}).get("within_session") or []
        return round(len(rows) / sessions, 3) if sessions else None
    return None


def outcomes(args) -> None:
    state = state_dir(find_root(args.root))
    figures = read_json(state / "figures.json", {})
    context = read_json(state / "context.json", {})
    generated = figures.get("meta", {}).get("generated_at", "")
    rows = [p for p in proposals(state) if p.get("state") == "applied" and p.get("metric")]
    if not rows:
        print("no applied proposal with a metric")
        return
    for p in rows:
        now = metric(p["metric"], figures, context)
        later = generated > (p.get("applied_at") or p.get("decided") or "")
        note = "" if later else " (collect again after the change has been in use)"
        print(
            f"{p['id']}: {p['metric']} baseline {p.get('baseline')}, when applied {p.get('applied_value')}, "
            f"now {now}{note}"
        )


def backup(args) -> None:
    state = state_dir(find_root(args.root))
    source = Path(args.file).expanduser()
    if not source.is_file():
        fail(f"no file {source}")
    folder = state / "backups"
    folder.mkdir(exist_ok=True)
    target = folder / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{source.name}"
    shutil.copy2(source, target)
    ledger(state, {"event": "backup", "file": str(source), "copy": str(target)})
    print(target)


# Notice


def notice(args) -> None:
    """One line when enough sessions ran since the last review; silent otherwise, and never an error. It reads only
    the first lines of transcripts written since then, so it stays fast enough for a SessionStart hook."""
    try:
        root = find_root(args.root)
        state = state_dir(root)
        figures = state / "figures.json"
        last = figures.stat().st_mtime if figures.exists() else None
        since = last or time.time() - DEFAULT_DAYS * 86400
        paths = scope_paths(root, False, [])
        count = 0
        for path, parent in find_claude(paths, since):
            if parent is None and in_scope(_first_cwd(path), paths):
                count += 1
        for path in find_codex(paths, since):
            if not _imported(path):
                count += 1
        if count >= args.min:
            if last:
                when = datetime.fromtimestamp(last).strftime("%Y-%m-%d")
                print(
                    f"curator: {count} sessions of {root.name} since the last review on {when}; /curator reviews them"
                )
            else:
                print(
                    f"curator: {count} sessions of {root.name} in {DEFAULT_DAYS} days and no review yet; "
                    "/curator reviews them"
                )
    except Exception:
        return


def _first_cwd(path: Path) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for _ in range(20):
                raw = handle.readline()
                if not raw:
                    break
                found = re.search(r'"cwd"\s*:\s*"([^"]+)"', raw)
                if found:
                    return json.loads(f'"{found.group(1)}"')
    except (OSError, ValueError):
        pass
    return ""


def _imported(path: Path) -> bool:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return "external-import-turn" in handle.read(20000)
    except OSError:
        return False


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="curator.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--root", help="the harness root (default: the git repo around the current directory)")
        return p

    p = common(sub.add_parser("scope", help="directories and transcripts of this harness"))
    p.add_argument("--cluster", action="store_true", help="add the repos of harness.yaml and their worktrees")
    p.add_argument("--path", action="append", help="add a directory (repeatable)")
    p = common(sub.add_parser("collect", help="figures, context inventory and report"))
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--runtime", help="claude,codex (default both)")
    p.add_argument(
        "--min-sessions",
        type=int,
        default=DEFAULT_MIN_SESSIONS,
        help="sessions a command, sequence or read needs before it counts as repeated",
    )
    p.add_argument("--cluster", action="store_true", help="add the repos of harness.yaml and their worktrees")
    p.add_argument("--path", action="append", help="add a directory (repeatable)")
    p.add_argument("--include-imported", action="store_true", help="keep Codex sessions imported from elsewhere")
    p.add_argument("--json", action="store_true")
    p = common(sub.add_parser("report", help="report.md again from the saved figures"))
    p.add_argument("--print", action="store_true", help="print the report instead of its path")
    p = common(sub.add_parser("show", help="one piece of evidence"))
    p.add_argument("ref")
    p.add_argument("--around", type=int, default=0, help="lines before and after")
    p.add_argument("--chars", type=int, default=3000, help="characters of the line itself")
    p = common(sub.add_parser("propose", help="check a proposal and file it"))
    p.add_argument("--file", required=True)
    p.add_argument("--force", action="store_true", help="file it even if a recent rejection covers it")
    p = common(sub.add_parser("list", help="proposals"))
    p.add_argument("--state", choices=STATES)
    p.add_argument("--json", action="store_true")
    p = common(sub.add_parser("decide", help="record what the person decided"))
    p.add_argument("id")
    p.add_argument("action", choices=sorted(ACTIONS))
    p.add_argument("--note")
    p.add_argument("--commit")
    common(sub.add_parser("outcomes", help="metrics of applied proposals, then and now"))
    p = common(sub.add_parser("backup", help="copy a file into the state before changing it"))
    p.add_argument("file")
    p = common(sub.add_parser("notice", help="a line for a SessionStart hook when a review is due"))
    p.add_argument("--min", type=int, default=NOTICE_SESSIONS)
    args = parser.parse_args(argv)
    if args.command == "scope":
        root = find_root(args.root)
        paths = scope_paths(root, args.cluster, args.path or [])
        sessions, skipped = load(paths, time.time() - DEFAULT_DAYS * 86400)
        print(f"root: {root}\nstate: {state_dir(root)}")
        for path in paths:
            mine = [s for s in sessions if in_scope(s.cwd, [path]) and s.kind != "subagent"]
            print(f"  {path}: {len(mine)} sessions in {DEFAULT_DAYS} days")
        if skipped:
            print("skipped: " + ", ".join(f"{n} {why}" for why, n in sorted(skipped.items())))
        return
    {
        "collect": collect,
        "report": report,
        "show": show,
        "propose": propose,
        "list": list_proposals,
        "decide": decide,
        "outcomes": outcomes,
        "backup": backup,
        "notice": notice,
    }[args.command](args)


if __name__ == "__main__":
    main()
