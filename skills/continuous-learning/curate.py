#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

LEARNED_DIRNAME = ".learned"
PROTECTED_NAMES = set()


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat(timespec="seconds")


def parse_iso(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def skills_root(base):
    return Path(base) / "skills"


def store_dir(base):
    return skills_root(base) / LEARNED_DIRNAME


def usage_path(base):
    return store_dir(base) / "usage.json"


def pending_dir(base):
    return store_dir(base) / "_pending"


def archive_dir(base):
    return store_dir(base) / ".archive"


def backups_dir(base):
    return store_dir(base) / ".backups"


def reports_dir(base):
    return store_dir(base) / "reports"


def processed_dir(base):
    return store_dir(base) / ".processed"


def default_usage():
    return {
        "version": 1,
        "curator": {"last_run_at": None, "paused": False},
        "skills": {},
    }


def load_usage(base):
    p = usage_path(base)
    if not p.exists():
        return default_usage()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default_usage()
    if "skills" not in data:
        data["skills"] = {}
    if "curator" not in data:
        data["curator"] = {"last_run_at": None, "paused": False}
    return data


def save_usage(base, data):
    p = usage_path(base)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sanitize_name(name):
    s = re.sub(r"[^a-z0-9-]+", "-", (name or "").lower()).strip("-")
    return s or "unnamed"


def register_skill(base, name, state, source_session, description=""):
    usage = load_usage(base)
    entry = usage["skills"].get(name, {})
    entry.setdefault("created_at", now_iso())
    entry["state"] = state
    entry["source_session"] = source_session
    entry["description"] = description
    entry.setdefault("use_count", 0)
    entry.pop("view_count", None)
    entry.setdefault("last_used_at", None)
    entry.setdefault("last_seen_session", None)
    entry.setdefault("pinned", False)
    usage["skills"][name] = entry
    save_usage(base, usage)


def active_skill_dir(base, name):
    return skills_root(base) / name


def is_learned_skill_dir(path):
    skill_md = path / "SKILL.md"
    if not skill_md.exists():
        return False
    head = skill_md.read_text(encoding="utf-8", errors="replace")[:600]
    return bool(re.search(r"^learned:\s*true\s*$", head, re.MULTILINE))


def record_usage_scan(base, messages, session_id):
    usage = load_usage(base)
    active = {
        name: e
        for name, e in usage["skills"].items()
        if e.get("state") in ("active", "stale")
    }
    if not active:
        return
    haystack_parts = []
    for m in messages:
        msg = m.get("message") if isinstance(m.get("message"), dict) else m
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, str):
            haystack_parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                inp = item.get("input") or {}
                for v in (
                    inp.get("file_path"),
                    inp.get("skill"),
                    inp.get("command"),
                    inp.get("path"),
                ):
                    if isinstance(v, str):
                        haystack_parts.append(v)
                if item.get("name") == "Skill" and isinstance(inp.get("skill"), str):
                    haystack_parts.append(inp["skill"])
    haystack = "\n".join(haystack_parts)
    changed = False
    for name, entry in active.items():
        if entry.get("last_seen_session") == session_id:
            continue
        needles = [f"skills/{name}/SKILL.md", f"skills/{name}/", f"Skill({name}"]
        hit = any(n in haystack for n in needles)
        word_hit = re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", haystack) is not None
        if hit or (word_hit and f"/{name}/" in haystack):
            entry["use_count"] = int(entry.get("use_count", 0)) + 1
            entry["last_used_at"] = now_iso()
            entry["last_seen_session"] = session_id
            changed = True
    if changed:
        save_usage(base, usage)


def idle_days(entry):
    ref = parse_iso(entry.get("last_used_at")) or parse_iso(entry.get("created_at"))
    if ref is None:
        return 0.0
    return (now() - ref).total_seconds() / 86400.0


def make_backup(base, reason):
    src = skills_root(base)
    if not src.exists():
        return None
    stamp = now().strftime("%Y%m%dT%H%M%SZ")
    out = backups_dir(base) / stamp
    out.mkdir(parents=True, exist_ok=True)
    tar_path = out / "skills.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        for child in src.iterdir():
            if child.name == LEARNED_DIRNAME:
                continue
            tar.add(child, arcname=child.name)
    learned = store_dir(base)
    if learned.exists():
        with tarfile.open(out / "learned.tar.gz", "w:gz") as tar:
            for child in learned.iterdir():
                if child.name in (".backups",):
                    continue
                tar.add(child, arcname=child.name)
    (out / "manifest.json").write_text(
        json.dumps({"reason": reason, "created_at": now_iso()}, indent=2) + "\n",
        encoding="utf-8",
    )
    prune_backups(base)
    return out


def prune_backups(base, keep=5):
    bd = backups_dir(base)
    if not bd.exists():
        return
    snaps = sorted([p for p in bd.iterdir() if p.is_dir()])
    for old in snaps[:-keep]:
        shutil.rmtree(old, ignore_errors=True)


def archive_skill(base, name, usage, reason="archived"):
    src = active_skill_dir(base, name)
    dest = archive_dir(base) / name
    archive_dir(base).mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    if src.exists():
        shutil.move(str(src), str(dest))
    entry = usage["skills"].setdefault(name, {})
    entry["state"] = "archived"
    entry["archived_at"] = now_iso()
    entry["archive_reason"] = reason


def restore_skill(base, name):
    usage = load_usage(base)
    entry = usage["skills"].get(name)
    if not entry:
        return False, f"unknown skill {name}"
    src = archive_dir(base) / name
    dest = active_skill_dir(base, name)
    if not src.exists():
        return False, f"not in archive: {name}"
    if dest.exists():
        return False, f"active skill already exists: {name}"
    shutil.move(str(src), str(dest))
    entry["state"] = "active"
    entry["last_used_at"] = now_iso()
    entry.pop("archived_at", None)
    save_usage(base, usage)
    return True, f"restored {name}"


SCOPE_RULE = """A learned skill belongs at the level its knowledge spans:

  --scope repo     one repo owns it        -> <cwd>/.claude/skills/<name>/
  --scope cluster  several repos share it  -> the evo-lms plugin in the cluster marketplace
  --scope machine  useful anywhere         -> ~/.claude/skills/ and ~/.opencode/skills/

Cross-cutting knowledge parked in one repo is invisible to its siblings: that is how
evo-lms-harness ended up holding 55 skills its 16 sibling repos could not see."""


def machine_skill_dirs():
    return [Path.home() / ".claude" / "skills", Path.home() / ".opencode" / "skills"]


def cluster_skill_dir(config):
    target = (config.get("promote") or {}).get("cluster_plugin_dir")
    if not target:
        return None
    return Path(os.path.expanduser(str(target)))


def promote_targets(base, name, scope, config):
    if scope == "repo":
        return [active_skill_dir(base, name)], None
    if scope == "machine":
        return [root / name for root in machine_skill_dirs() if root.parent.is_dir()], None
    plugin = cluster_skill_dir(config)
    if plugin is None:
        return [], (
            "no cluster target configured: set promote.cluster_plugin_dir in "
            ".claude/continuous-learning.json to the plugin's skills/ directory"
        )
    return [plugin / name], None


def promote_skill(base, name, scope, config):
    usage = load_usage(base)
    entry = usage["skills"].get(name)
    src = pending_dir(base) / name
    from_active = False
    if not src.exists():
        src = active_skill_dir(base, name)
        from_active = src.exists()
        if not from_active:
            return False, f"not pending and not active: {name}"
        if scope == "repo":
            return False, f"{name} is already active in this repo; pick --scope cluster or machine"

    dests, err = promote_targets(base, name, scope, config)
    if err:
        return False, err
    if not dests:
        return False, f"no destination exists for --scope {scope} on this machine"
    for dest in dests:
        if dest.exists():
            return False, f"already exists at {dest}"

    first = dests[0]
    first.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(first))
    for dest in dests[1:]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(first), str(dest))

    if scope == "repo":
        if entry is None:
            entry = {"created_at": now_iso(), "use_count": 0, "pinned": False}
            usage["skills"][name] = entry
        entry["state"] = "active"
        entry["last_used_at"] = now_iso()
    elif entry is not None:
        entry["state"] = "promoted-out"
        entry["promoted_to"] = [str(d) for d in dests]
        entry["last_used_at"] = now_iso()
    save_usage(base, usage)
    origin = "active" if from_active else "pending"
    return True, f"promoted {name} ({origin} -> {scope}): {', '.join(str(d) for d in dests)}"


def lifecycle_pass(base, config, usage, report, dry_run, archive_ok=False):
    stale_after = float(config.get("curator", {}).get("stale_after_days", 30))
    archive_after = float(config.get("curator", {}).get("archive_after_days", 90))
    for name, entry in list(usage["skills"].items()):
        if entry.get("state") not in ("active", "stale"):
            continue
        if entry.get("pinned") or name in PROTECTED_NAMES:
            continue
        d = idle_days(entry)
        if d >= archive_after:
            record = {"name": name, "idle_days": round(d, 1)}
            if archive_ok and not dry_run:
                report["archived"].append(record)
                archive_skill(base, name, usage, reason=f"idle {round(d)}d")
            else:
                report["archive_candidates"].append(record)
        elif d >= stale_after and entry.get("state") != "stale":
            report["staled"].append({"name": name, "idle_days": round(d, 1)})
            if not dry_run:
                entry["state"] = "stale"
        elif d < stale_after and entry.get("state") == "stale":
            if not dry_run:
                entry["state"] = "active"


def read_skill_body(base, name):
    p = active_skill_dir(base, name) / "SKILL.md"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def consolidate_pass(base, config, usage, report, dry_run):
    active = [
        name
        for name, e in usage["skills"].items()
        if e.get("state") in ("active", "stale") and not e.get("pinned")
    ]
    if len(active) < 2:
        return
    catalog = []
    for name in active:
        body = read_skill_body(base, name)
        desc = usage["skills"][name].get("description", "")
        catalog.append(f"### {name}\ndescription: {desc}\n{body[:1200]}")
    prompt = (
        "You are a skill librarian. Below are agent-learned Claude Code skills.\n"
        "Find groups that overlap heavily (same workflow/topic). For each group,\n"
        "pick ONE keep target and list the others as duplicates to archive.\n"
        "Be conservative: only group genuine near-duplicates. Return ONLY JSON:\n"
        '{"merges":[{"keep":"name","archive":["name2"],"reason":"..."}]}\n'
        "If nothing overlaps return {\"merges\":[]}.\n\n"
        + "\n\n".join(catalog)
    )
    model = config.get("curator", {}).get("model") or config.get("claude_model", "claude-haiku-4-5")
    timeout = int(config.get("claude_timeout_seconds", 600))
    env = os.environ.copy()
    env["CONTINUOUS_LEARNING_CHILD"] = "1"
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--model", model],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
    except Exception as e:
        report["consolidate_error"] = str(e)
        return
    if proc.returncode != 0:
        report["consolidate_error"] = proc.stderr[:300]
        return
    m = re.search(r"\{[\s\S]*\}", proc.stdout)
    if not m:
        return
    try:
        data = json.loads(m.group(0))
    except Exception:
        return
    for merge in data.get("merges", []):
        keep = sanitize_name(merge.get("keep", ""))
        if keep not in usage["skills"]:
            continue
        for dup in merge.get("archive", []):
            dup = sanitize_name(dup)
            if dup == keep or dup not in usage["skills"]:
                continue
            if usage["skills"][dup].get("pinned"):
                continue
            report["consolidated"].append({"keep": keep, "archived": dup, "reason": merge.get("reason", "")})
            if not dry_run:
                archive_skill(base, dup, usage, reason=f"merged into {keep}")
                note = f"\n\n<!-- consolidated: absorbed `{dup}` on {now_iso()} -->\n"
                kp = active_skill_dir(base, keep) / "SKILL.md"
                if kp.exists():
                    kp.write_text(kp.read_text(encoding="utf-8") + note, encoding="utf-8")


def write_report(base, report, dry_run):
    stamp = now().strftime("%Y%m%dT%H%M%SZ")
    out = reports_dir(base) / stamp
    out.mkdir(parents=True, exist_ok=True)
    (out / "run.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        f"# Curator run {stamp}",
        f"- dry_run: {dry_run}",
        f"- archived: {len(report['archived'])}",
        f"- staled: {len(report['staled'])}",
        f"- consolidated: {len(report['consolidated'])}",
        "",
    ]
    for k in ("archived", "staled", "consolidated"):
        if report[k]:
            lines.append(f"## {k}")
            for item in report[k]:
                lines.append(f"- {json.dumps(item, ensure_ascii=False)}")
            lines.append("")
    (out / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def run_curator(base, config, consolidate=False, dry_run=False, backup=True, archive_ok=False):
    usage = load_usage(base)
    if usage["curator"].get("paused"):
        return {"skipped": "paused"}
    report = {
        "started_at": now_iso(),
        "archived": [],
        "archive_candidates": [],
        "staled": [],
        "consolidated": [],
        "dry_run": dry_run,
    }
    if backup and not dry_run:
        b = make_backup(base, reason="pre-curator")
        report["backup"] = str(b) if b else None
    lifecycle_pass(base, config, usage, report, dry_run, archive_ok=archive_ok)
    if consolidate or config.get("curator", {}).get("consolidate", False):
        consolidate_pass(base, config, usage, report, dry_run)
    if not dry_run:
        usage["curator"]["last_run_at"] = now_iso()
        save_usage(base, usage)
    report["report_dir"] = str(write_report(base, report, dry_run))
    return report


def maybe_auto_curate(base, config):
    cur = config.get("curator", {})
    if not cur.get("enabled", True):
        return
    usage = load_usage(base)
    if usage["curator"].get("paused"):
        return
    last = parse_iso(usage["curator"].get("last_run_at"))
    interval_h = float(cur.get("interval_hours", 168))
    if last is not None:
        elapsed_h = (now() - last).total_seconds() / 3600.0
        if elapsed_h < interval_h:
            return
    run_curator(base, config, consolidate=cur.get("auto_consolidate", False), dry_run=False, backup=True)


def load_config(cwd, config_path):
    cfg = {}
    if config_path and Path(config_path).exists():
        cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    proj = Path(cwd) / ".claude" / "continuous-learning.json"
    if proj.exists():
        try:
            override = json.loads(proj.read_text(encoding="utf-8"))
            for k, v in override.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except Exception:
            pass
    return cfg


def cmd_status(base):
    usage = load_usage(base)
    cur = usage["curator"]
    print(f"last_run_at: {cur.get('last_run_at')}  paused: {cur.get('paused')}")
    rows = []
    for name, e in usage["skills"].items():
        rows.append((round(idle_days(e), 1), name, e.get("state"), e.get("use_count", 0), e.get("pinned")))
    rows.sort(reverse=True)
    print(f"{'idle_d':>7}  {'state':<9} {'used':>4} pin  name")
    for idle, name, state, used, pinned in rows:
        print(f"{idle:>7}  {state:<9} {used:>4}  {'*' if pinned else ' '}   {name}")


def cmd_pin(base, name, pinned):
    usage = load_usage(base)
    if name not in usage["skills"]:
        print(f"unknown skill: {name}", file=sys.stderr)
        return 1
    usage["skills"][name]["pinned"] = pinned
    save_usage(base, usage)
    print(f"{'pinned' if pinned else 'unpinned'} {name}")
    return 0


def cmd_list_archived(base):
    ad = archive_dir(base)
    if not ad.exists():
        print("(no archived skills)")
        return
    for p in sorted(ad.iterdir()):
        if p.is_dir():
            print(p.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=[
        "run", "status", "pin", "unpin", "promote", "restore",
        "list-archived", "prune", "pause", "resume",
    ])
    ap.add_argument("name", nargs="?")
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--config")
    ap.add_argument("--consolidate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--scope", choices=["repo", "cluster", "machine"], help="where a promoted skill lands; required for promote")
    ap.add_argument("--yes", action="store_true", help="let the curator actually archive its candidates")
    args = ap.parse_args()

    if not args.config:
        args.config = str(Path(__file__).parent / "config.json")
    base = Path(args.cwd) / ".claude"
    config = load_config(args.cwd, args.config)

    if args.command == "status":
        cmd_status(base)
    elif args.command == "run":
        report = run_curator(base, config, consolidate=args.consolidate, dry_run=args.dry_run, archive_ok=args.yes)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        pending_archive = report.get("archive_candidates") or []
        if pending_archive:
            print(f"\n{len(pending_archive)} skill(s) idle past the archive threshold, left in place:", file=sys.stderr)
            for c in pending_archive:
                print(f"  {c['name']} ({c['idle_days']}d idle)", file=sys.stderr)
            print("Re-run with --yes to archive them. Read the caveat about use_count first.", file=sys.stderr)
    elif args.command == "pin":
        return cmd_pin(base, args.name, True)
    elif args.command == "unpin":
        return cmd_pin(base, args.name, False)
    elif args.command == "promote":
        if not args.scope:
            print(SCOPE_RULE, file=sys.stderr)
            print("\nRe-run with --scope repo|cluster|machine.", file=sys.stderr)
            return 1
        if args.all:
            pd = pending_dir(base)
            if pd.exists():
                for p in sorted(pd.iterdir()):
                    if p.is_dir():
                        ok, msg = promote_skill(base, p.name, args.scope, config)
                        print(msg)
        elif args.name:
            ok, msg = promote_skill(base, args.name, args.scope, config)
            print(msg)
            return 0 if ok else 1
        else:
            print("need a name or --all", file=sys.stderr)
            return 1
    elif args.command == "restore":
        ok, msg = restore_skill(base, args.name)
        print(msg)
        return 0 if ok else 1
    elif args.command == "list-archived":
        cmd_list_archived(base)
    elif args.command == "prune":
        usage = load_usage(base)
        report = {"started_at": now_iso(), "archived": [], "staled": [], "consolidated": [], "dry_run": False}
        make_backup(base, reason="pre-prune")
        for name, e in list(usage["skills"].items()):
            if e.get("state") in ("active", "stale") and not e.get("pinned") and idle_days(e) >= args.days:
                report["archived"].append({"name": name, "idle_days": round(idle_days(e), 1)})
                archive_skill(base, name, usage, reason=f"prune>={args.days}d")
        save_usage(base, usage)
        print(f"archived {len(report['archived'])} skill(s)")
    elif args.command in ("pause", "resume"):
        usage = load_usage(base)
        usage["curator"]["paused"] = args.command == "pause"
        save_usage(base, usage)
        print(args.command)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
