#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _transcript as T

try:
    import yaml
except ImportError:
    print("PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"
REGISTRY = Path.home() / ".claude" / "harness" / "registry.json"
MANIFEST = "harness.yaml"

MAP_NAMES = ["AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md"]
MAP_LINE_BUDGET = 150
BOOT_NAMES = ["init.sh", "init.ps1", "Makefile", "Taskfile.yml", "justfile"]
PROGRESS_NAMES = ["claude-progress.txt", "PROGRESS.md", "CHANGELOG.md", "docs/PROGRESS.md"]
PRINCIPLE_NAMES = ["principles/golden-principles.md", "GOLDEN_PRINCIPLES.md", "docs/golden-principles.md"]
CI_DIRS = [".github/workflows", ".gitlab-ci.yml", ".circleci"]
LINT_NAMES = [
    ".eslintrc", ".eslintrc.json", ".eslintrc.js", "eslint.config.js", "eslint.config.mjs",
    "ruff.toml", ".ruff.toml", ".flake8", "setup.cfg", "pyproject.toml",
    ".golangci.yml", "analysis_options.yaml", "tslint.json",
]
E2E_NAMES = ["playwright.config.ts", "playwright.config.js", "cypress.config.ts", "cypress.config.js"]


def now():
    return datetime.now().astimezone()


def iso(dt=None):
    return (dt or now()).isoformat(timespec="seconds")


def slug(s):
    s = re.sub(r"[^a-z0-9-]+", "-", (s or "").lower()).strip("-")
    return s or "unnamed"


def read_yaml(path):
    p = Path(path)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_yaml(obj, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True, default_flow_style=False)


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def write_json(obj, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def git(repo, *args, timeout=20):
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo)] + list(args),
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def is_git_repo(p):
    return (Path(p) / ".git").exists()


def expand(p, default=None):
    s = str(p or "").strip()
    if not s:
        return Path(default) if default is not None else None
    return Path(s).expanduser()


def portable(p):
    p = Path(p)
    try:
        return "~/" + p.relative_to(Path.home()).as_posix()
    except ValueError:
        return str(p)


def load_registry():
    return read_json(REGISTRY, {"clusters": []}) or {"clusters": []}


def save_registry(reg):
    write_json(reg, REGISTRY)


def register(root, name, workspace, repo_paths):
    reg = load_registry()
    reg["clusters"] = [c for c in reg.get("clusters", []) if c.get("root") != str(root)]
    reg["clusters"].append({
        "name": name,
        "root": str(root),
        "workspace": str(workspace),
        "repos": [str(p) for p in repo_paths],
        "registered_at": iso(),
    })
    save_registry(reg)


def find_root(start=None, name=None):
    if os.environ.get("HARNESS_ROOT"):
        p = Path(os.environ["HARNESS_ROOT"])
        if (p / MANIFEST).exists():
            return p

    reg = load_registry()
    if name:
        for c in reg.get("clusters", []):
            if c.get("name") == name and (Path(c["root"]) / MANIFEST).exists():
                return Path(c["root"])
        return None

    cur = Path(start or Path.cwd()).resolve()
    for p in [cur] + list(cur.parents):
        if (p / MANIFEST).exists():
            return p
        if (p / ".harness" / MANIFEST).exists():
            return p / ".harness"

    best = None
    best_len = -1
    for c in reg.get("clusters", []):
        for rp in c.get("repos", []) + [c.get("workspace", "")]:
            if not rp:
                continue
            try:
                rpp = Path(rp).resolve()
            except OSError:
                continue
            if cur == rpp or rpp in cur.parents:
                if len(str(rpp)) > best_len and (Path(c["root"]) / MANIFEST).exists():
                    best, best_len = Path(c["root"]), len(str(rpp))
    return best


def need_root(args):
    root = find_root(getattr(args, "root", None) or None, getattr(args, "cluster", None))
    if root is None:
        print("No harness found for this location.", file=sys.stderr)
        print("Run: python harness.py init --workspace <dir> --name <cluster>", file=sys.stderr)
        sys.exit(1)
    return root


def manifest(root):
    m = read_yaml(Path(root) / MANIFEST)
    if m is None:
        print(f"Missing {MANIFEST} at {root}", file=sys.stderr)
        sys.exit(1)
    return m


def repo_paths(root, m, present_only=True):
    ws = expand(m.get("workspace"), default=root)
    out = []
    for r in m.get("repos", []):
        if present_only and not r.get("present", True):
            continue
        p = expand(r.get("path"), default=ws / r["name"])
        if not p.is_absolute():
            p = (ws / p).resolve()
        out.append((r, p))
    return out


def detect_role(p):
    has = lambda *names: any((p / n).exists() for n in names)
    if has("pubspec.yaml"):
        return "mobile"
    if has(*E2E_NAMES):
        return "e2e"
    if has("docusaurus.config.js", "docusaurus.config.ts", "mkdocs.yml", "book.toml"):
        return "docs"
    if has("terraform.tf", "main.tf", "Chart.yaml", "kustomization.yaml"):
        return "infra"
    pkg = p / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
            if any(k.startswith("@angular") for k in deps) or "react" in deps or "vue" in deps or "next" in deps or "svelte" in deps:
                return "frontend"
            if "express" in deps or "fastify" in deps or "@nestjs/core" in deps:
                return "backend"
            return "node"
        except (json.JSONDecodeError, OSError):
            return "node"
    if has("manage.py"):
        return "backend"
    if has("go.mod", "Cargo.toml"):
        return "backend"
    if has("pyproject.toml", "setup.py"):
        return "python"
    if len(list(p.glob("*.md"))) >= 5:
        return "docs"
    return "unknown"


def count_lines(p):
    try:
        return len(p.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def count_links(p):
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return len(re.findall(r"\[[^\]]+\]\([^)]+\)", txt)) + len(re.findall(r"`[^`]*\.(?:md|sh|py|json|ya?ml)`", txt))


def find_map(p):
    for n in MAP_NAMES:
        f = p / n
        if f.exists():
            return f
    return None


def has_test_cmd(p):
    pkg = p / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if "test" in (data.get("scripts") or {}):
                return True
        except (json.JSONDecodeError, OSError):
            pass
    return any((p / n).exists() for n in ["pytest.ini", "tox.ini", "Makefile", "manage.py"] + E2E_NAMES)


def find_feature_spec(p):
    for cand in ["feature_list.json", "features.json", "acceptance.json", "docs/feature_list.json"]:
        if (p / cand).exists():
            return cand
    return None


def inventory(p):
    mp = find_map(p)
    docs = p / "docs"
    skills = p / ".claude" / "skills"
    inv = {
        "map": str(mp.relative_to(p)) if mp else None,
        "map_lines": count_lines(mp) if mp else 0,
        "map_links": count_links(mp) if mp else 0,
        "docs_dir": docs.is_dir(),
        "docs_index": any((docs / n).exists() for n in ["index.md", "README.md"]) if docs.is_dir() else False,
        "docs_subdirs": sorted([d.name for d in docs.iterdir() if d.is_dir()]) if docs.is_dir() else [],
        "boot": [n for n in BOOT_NAMES if (p / n).exists()],
        "test_cmd": has_test_cmd(p),
        "e2e": [n for n in E2E_NAMES if (p / n).exists()],
        "progress": [n for n in PROGRESS_NAMES if (p / n).exists()],
        "principles": [n for n in PRINCIPLE_NAMES if (p / n).exists()],
        "feature_spec": find_feature_spec(p),
        "lint": [n for n in LINT_NAMES if (p / n).exists()],
        "ci": [n for n in CI_DIRS if (p / n).exists()],
        "plans_dir": (p / "docs" / "exec-plans").is_dir() or (p / "plans").is_dir(),
        "skills": sorted([d.name for d in skills.iterdir() if d.is_dir() and not d.name.startswith(".")]) if skills.is_dir() else [],
    }
    return inv


WIP_RE = re.compile(r"^(wip|fix|update|temp|test|asdf|\.+|chore)\b", re.I)


def git_state(p):
    branch = git(p, "rev-parse", "--abbrev-ref", "HEAD")
    status = git(p, "status", "--porcelain")
    subjects = (git(p, "log", "-20", "--format=%s") or "").splitlines()
    last = git(p, "log", "-1", "--format=%cI")
    low_quality = sum(1 for s in subjects if WIP_RE.match(s.strip()) and len(s.strip()) < 25)
    return {
        "branch": branch,
        "dirty": bool(status),
        "last_commit": last,
        "commits_sampled": len(subjects),
        "low_quality_msgs": low_quality,
    }


def cmd_init(args):
    ws = Path(args.workspace).resolve()
    if not ws.is_dir():
        print(f"Workspace not found: {ws}", file=sys.stderr)
        sys.exit(1)

    root = Path(args.root).resolve() if args.root else (ws / ".harness")
    if (root / MANIFEST).exists() and not args.force:
        print(f"Harness already exists at {root}. Use --force to overwrite the manifest.", file=sys.stderr)
        sys.exit(1)

    include = [x.strip() for x in (args.include or "").split(",") if x.strip()]
    exclude = [x.strip() for x in (args.exclude or "").split(",") if x.strip()]

    repos = []
    found = []
    for d in sorted(ws.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if not is_git_repo(d):
            continue
        if include and not any(re.search(pat, d.name) for pat in include):
            continue
        if exclude and any(re.search(pat, d.name) for pat in exclude):
            continue
        origin = git(d, "remote", "get-url", "origin") or ""
        repos.append({
            "name": d.name,
            "path": portable(d),
            "role": detect_role(d),
            "present": True,
            "origin": origin,
        })
        found.append(d)

    if not repos:
        print(f"No git repos matched under {ws}", file=sys.stderr)
        sys.exit(1)

    m = {
        "name": args.name,
        "workspace": portable(ws),
        "created_at": iso(),
        "repos": repos,
        "garden": {
            "min_sessions": 3,
            "min_occurrences": 2,
            "max_proposals_per_run": 5,
            "lookback_days": 14,
            "model": "claude-haiku-4-5",
        },
    }
    write_yaml(m, root / MANIFEST)

    for sub in ["principles", "docs", "plans/active", "plans/completed",
                "state/sessions", "state/processed",
                "proposals/_pending", "proposals/applied", "proposals/rejected"]:
        (root / sub).mkdir(parents=True, exist_ok=True)

    for tpl, dest in [
        ("contracts.yaml", root / "contracts.yaml"),
        ("CLUSTER.md", root / "CLUSTER.md"),
        ("golden-principles.md", root / "principles" / "golden-principles.md"),
        ("invariants.md", root / "principles" / "invariants.md"),
    ]:
        src = TEMPLATES / tpl
        if src.exists() and not dest.exists():
            txt = src.read_text(encoding="utf-8")
            txt = txt.replace("{{CLUSTER}}", args.name)
            txt = txt.replace("{{REPOS}}", "\n".join(f"- `{r['name']}` ({r['role']})" for r in repos))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(txt, encoding="utf-8")

    register(root, args.name, ws, found)

    print(f"Harness root: {root}")
    print(f"Cluster '{args.name}' with {len(repos)} repo(s):")
    for r in repos:
        print(f"  {r['name']:<32} {r['role']}")
    print()
    print("Next: python harness.py audit")
    print("Repos that exist but were not cloned locally must be added to harness.yaml by hand with present: false")


def cmd_scan(args):
    root = need_root(args)
    m = manifest(root)
    out = {"scanned_at": iso(), "cluster": m.get("name"), "repos": {}}
    for r, p in repo_paths(root, m):
        if not p.is_dir():
            out["repos"][r["name"]] = {"missing_on_disk": True, "role": r.get("role")}
            continue
        out["repos"][r["name"]] = {
            "path": str(p),
            "role": r.get("role"),
            "git": git_state(p),
            "inventory": inventory(p),
        }
    write_json(out, root / "state" / "scan.json")
    print(f"Scanned {len(out['repos'])} repo(s) -> {root / 'state' / 'scan.json'}")
    return out


DIMS = {
    1: "Map", 2: "System of record", 3: "Bootability", 4: "Feedback loops",
    5: "Inter-session memory", 6: "Mechanical enforcement", 7: "Work spec",
    8: "Entropy control", 9: "Cluster manifest", 10: "Contract registry",
    11: "Cross-repo coordination",
}


def score_repo(rec):
    inv = rec["inventory"]
    g = rec["git"]
    s = {}
    ev = {}

    if not inv["map"]:
        s[1] = 0
        ev[1] = "no AGENTS.md or CLAUDE.md at repo root"
    elif inv["map_lines"] > MAP_LINE_BUDGET:
        s[1] = 1
        ev[1] = f"{inv['map']} is {inv['map_lines']} lines (budget {MAP_LINE_BUDGET}); likely an encyclopedia, not a map"
    elif inv["map_links"] < 3:
        s[1] = 1
        ev[1] = f"{inv['map']} has {inv['map_links']} outbound pointers; a map should point outward"
    else:
        s[1] = 2
        ev[1] = f"{inv['map']}: {inv['map_lines']} lines, {inv['map_links']} pointers"

    if not inv["docs_dir"]:
        s[2] = 0
        ev[2] = "no docs/ directory"
    elif not inv["docs_index"]:
        s[2] = 1
        ev[2] = "docs/ exists but has no index"
    elif not inv["docs_subdirs"]:
        s[2] = 1
        ev[2] = "docs/ is flat; no structure to disclose progressively"
    else:
        s[2] = 2
        ev[2] = f"docs/ with index and {len(inv['docs_subdirs'])} subdir(s)"

    if not inv["boot"]:
        s[3] = 0
        ev[3] = "no init.sh / init.ps1 / Makefile; every session re-derives how to run this"
    elif "init.sh" in inv["boot"] or "init.ps1" in inv["boot"]:
        s[3] = 2
        ev[3] = f"boot via {', '.join(inv['boot'])}"
    else:
        s[3] = 1
        ev[3] = f"only {', '.join(inv['boot'])}; no dedicated init script"

    fb = 0
    fbn = []
    if inv["test_cmd"]:
        fb += 1
        fbn.append("test command")
    if inv["e2e"]:
        fb += 1
        fbn.append("e2e driver")
    s[4] = min(fb, 2)
    ev[4] = ("has " + ", ".join(fbn)) if fbn else "no test command and no e2e driver; the agent cannot see this run"

    mem = 0
    memn = []
    if inv["progress"]:
        mem += 1
        memn.append(inv["progress"][0])
    if inv["plans_dir"]:
        mem += 1
        memn.append("plans dir")
    if g.get("commits_sampled") and g["low_quality_msgs"] > g["commits_sampled"] * 0.4:
        ev[5] = f"{g['low_quality_msgs']}/{g['commits_sampled']} recent commit messages carry no intent"
        s[5] = min(mem, 1)
    else:
        s[5] = min(mem, 2)
        ev[5] = ("has " + ", ".join(memn)) if memn else "no progress file and no checked-in plans"

    enf = 0
    enfn = []
    if inv["lint"]:
        enf += 1
        enfn.append("lint config")
    if inv["ci"]:
        enf += 1
        enfn.append("CI")
    s[6] = min(enf, 2)
    ev[6] = ("has " + ", ".join(enfn)) if enfn else "nothing mechanical holds any rule here"

    if inv["feature_spec"]:
        s[7] = 2
        ev[7] = f"work spec: {inv['feature_spec']}"
    else:
        s[7] = 0
        ev[7] = "no structured acceptance/feature list; 'done' is whatever the agent decides"

    if inv["principles"]:
        s[8] = 2
        ev[8] = f"principles: {inv['principles'][0]}"
    else:
        s[8] = 0
        ev[8] = "no golden principles; drift has nothing to push back against"

    return s, ev


def score_cluster(root, m, scan):
    s = {}
    ev = {}

    declared = m.get("repos", [])
    absent_unmarked = [r["name"] for r in declared if r.get("present", True) and scan["repos"].get(r["name"], {}).get("missing_on_disk")]
    roles = sum(1 for r in declared if r.get("role") and r["role"] != "unknown")
    if not declared:
        s[9], ev[9] = 0, "manifest lists no repos"
    elif absent_unmarked:
        s[9], ev[9] = 1, f"declared but not on disk (and not marked present: false): {', '.join(absent_unmarked)}"
    elif roles < len(declared):
        s[9], ev[9] = 1, f"{len(declared) - roles} repo(s) have no role assigned"
    else:
        s[9], ev[9] = 2, f"{len(declared)} repo(s), all with roles"

    c = read_yaml(root / "contracts.yaml") or {}
    seams = c.get("seams") or []
    if not seams:
        s[10], ev[10] = 0, "no seams registered; nothing checks that repos still agree with each other"
    else:
        no_verify = [x.get("name") for x in seams if not x.get("verify")]
        if no_verify:
            s[10], ev[10] = 1, f"{len(no_verify)}/{len(seams)} seam(s) have no verify method: {', '.join(str(n) for n in no_verify[:3])}"
        else:
            s[10], ev[10] = 2, f"{len(seams)} seam(s), all with a verify method"

    active = list((root / "plans" / "active").glob("*.yaml")) if (root / "plans" / "active").is_dir() else []
    feature_branches = [
        n for n, rec in scan["repos"].items()
        if not rec.get("missing_on_disk") and rec.get("git", {}).get("branch") not in (None, "main", "master", "develop", "HEAD")
    ]
    if len(feature_branches) >= 2 and not active:
        s[11], ev[11] = 0, f"{len(feature_branches)} repos on feature branches ({', '.join(feature_branches[:4])}) with no exec-plan; this change is being improvised"
    elif not active:
        s[11], ev[11] = 1, "no active exec-plans (fine if no cross-repo work is in flight)"
    else:
        s[11], ev[11] = 2, f"{len(active)} active exec-plan(s)"

    return s, ev


def load_scan(root, refresh=False):
    p = root / "state" / "scan.json"
    if refresh or not p.exists():
        return cmd_scan(argparse.Namespace(root=str(root), cluster=None))
    return read_json(p)


def cmd_audit(args):
    root = need_root(args)
    m = manifest(root)
    scan = load_scan(root, refresh=not args.no_scan)

    gaps = []
    per_repo = {}
    for name, rec in scan["repos"].items():
        if rec.get("missing_on_disk"):
            continue
        s, ev = score_repo(rec)
        per_repo[name] = {"scores": s, "evidence": ev}
        for d, sc in s.items():
            if sc < 2:
                gaps.append({
                    "scope": name, "dim": d, "dim_name": DIMS[d], "score": sc,
                    "evidence": ev[d], "action": ACTIONS[d],
                })

    cs, cev = score_cluster(root, m, scan)
    for d, sc in cs.items():
        if sc < 2:
            gaps.append({
                "scope": "<cluster>", "dim": d, "dim_name": DIMS[d], "score": sc,
                "evidence": cev[d], "action": ACTIONS[d],
            })

    gaps.sort(key=lambda g: (g["score"], -WEIGHT.get(g["dim"], 1), g["scope"]))

    write_json({
        "audited_at": iso(), "cluster": m.get("name"),
        "gaps": gaps, "per_repo": per_repo, "cluster_scores": cs, "cluster_evidence": cev,
    }, root / "state" / "gaps.json")

    lines = [f"# Harness audit: {m.get('name')}", "", f"Audited {iso()}", ""]
    top = gaps[: args.top]
    if not top:
        lines.append("No gaps below score 2. Push the load-bearing dimensions to 3 (enforced) next.")
    else:
        lines.append(f"## Top {len(top)} gaps")
        lines.append("")
        for g in top:
            lines.append(f"### {g['scope']} - {g['dim_name']} (score {g['score']}/3)")
            lines.append(f"- Evidence: {g['evidence']}")
            lines.append(f"- Next artifact: {g['action']}")
            lines.append("")
    lines.append(f"({len(gaps)} gaps total; full detail in state/gaps.json)")
    report = "\n".join(lines) + "\n"
    (root / "REPORT.md").write_text(report, encoding="utf-8")

    print(report)
    print(f"Wrote {root / 'REPORT.md'}")


WEIGHT = {3: 3, 5: 3, 7: 3, 10: 3, 11: 3, 1: 2, 6: 2, 4: 2, 2: 1, 8: 1, 9: 1}

ACTIONS = {
    1: "write an AGENTS.md that is a ~100-line table of contents pointing into docs/, not an encyclopedia",
    2: "create docs/ with an index and at least design-docs/ and references/",
    3: "write init.sh + init.ps1 that boots the dev env, and name it in the map",
    4: "give the agent a way to see this run: a test command, and an e2e driver for anything with a UI",
    5: "add a progress file and require a descriptive git commit at the end of every session",
    6: "add a linter for the rules that documentation keeps failing to hold; write remediation into the error message",
    7: "write feature_list.json with end-to-end behaviors, all passes: false, and forbid editing it except to flip status",
    8: "write principles/golden-principles.md and schedule a gardening pass",
    9: "fix harness.yaml: assign roles, and mark repos that are not cloned locally as present: false",
    10: "register the cross-repo seams in contracts.yaml, each with an owner, consumers, and a verify method",
    11: "create a cross-repo exec-plan in plans/active/ with an explicit merge order",
}


SIBLING_RE = re.compile(r"\.\./([A-Za-z0-9._-]+)/([A-Za-z0-9._/-]*)")


def cmd_doctor(args):
    root = need_root(args)
    m = manifest(root)
    scan = load_scan(root, refresh=True)
    findings = []

    declared = {r["name"] for r in m.get("repos", [])}
    for r, p in repo_paths(root, m):
        if not p.is_dir():
            findings.append(("manifest", r["name"], "declared present but not on disk; set present: false or clone it"))

    ws = expand(m.get("workspace"), default=root)
    for r, p in repo_paths(root, m):
        if not p.is_dir():
            continue
        for md in list(p.glob("*.md")) + list(p.glob(".claude/*.md")) + list((p / "docs").rglob("*.md"))[:200]:
            try:
                txt = md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for sib, rest in SIBLING_RE.findall(txt):
                if sib in (".", "..") or sib == p.name:
                    continue
                target = (p.parent / sib / rest).resolve() if rest else (p.parent / sib).resolve()
                if not target.exists():
                    kind = "dangling sibling repo" if sib in declared or (ws / sib).exists() is False else "dangling sibling path"
                    findings.append(("link", r["name"], f"{md.relative_to(p)} points at ../{sib}/{rest} which does not exist ({kind})"))

    for name, rec in scan["repos"].items():
        if rec.get("missing_on_disk"):
            continue
        inv = rec["inventory"]
        if inv["map"] and inv["map_lines"] > MAP_LINE_BUDGET:
            findings.append(("map", name, f"{inv['map']} is {inv['map_lines']} lines; over the {MAP_LINE_BUDGET}-line budget, it is crowding out context"))

    skill_owner = {}
    for name, rec in scan["repos"].items():
        if rec.get("missing_on_disk"):
            continue
        for sk in rec["inventory"]["skills"]:
            skill_owner.setdefault(sk, []).append(name)
    for sk, owners in skill_owner.items():
        if len(owners) > 1:
            findings.append(("skill", ", ".join(owners), f"skill '{sk}' is duplicated across {len(owners)} repos; it belongs at cluster level"))

    counts = {n: len(r["inventory"]["skills"]) for n, r in scan["repos"].items() if not r.get("missing_on_disk")}
    if counts and len(counts) > 1:
        top = max(counts, key=counts.get)
        rest = sorted(v for k, v in counts.items() if k != top)
        if counts[top] >= 10 and counts[top] > 4 * max(1, (sum(rest) / max(1, len(rest)))):
            findings.append(("hub-trap", top, f"{top} holds {counts[top]} skills while its siblings hold {rest}; cross-cutting knowledge is trapped there"))

    c = read_yaml(root / "contracts.yaml") or {}
    for seam in (c.get("seams") or []):
        if not seam.get("verify"):
            findings.append(("seam", seam.get("owner", "?"), f"seam '{seam.get('name')}' has no verify method; it is documentation, not a harness"))
        owner = seam.get("owner")
        if owner and owner not in declared:
            findings.append(("seam", owner, f"seam '{seam.get('name')}' names owner '{owner}' which is not in harness.yaml"))

    for plan_file in (root / "plans" / "active").glob("*.yaml"):
        plan = read_yaml(plan_file) or {}
        for entry in plan.get("repos", []):
            rn, want = entry.get("repo"), entry.get("branch")
            rec = scan["repos"].get(rn)
            if not rec or rec.get("missing_on_disk"):
                findings.append(("plan", rn or "?", f"{plan_file.name} names repo '{rn}' which is not in the cluster"))
                continue
            actual = rec.get("git", {}).get("branch")
            if want and actual and want != actual and entry.get("status") not in {"pending", "todo"}:
                findings.append(("plan", rn, f"{plan_file.name} expects branch '{want}' but {rn} is on '{actual}'"))

    reg = load_registry()
    for cl in reg.get("clusters", []):
        if not (Path(cl["root"]) / MANIFEST).exists():
            findings.append(("registry", cl.get("name", "?"), f"registry points at {cl['root']} which has no {MANIFEST}; stale entry"))

    if not findings:
        print("doctor: no findings.")
        return

    print(f"doctor: {len(findings)} finding(s)\n")
    by_kind = {}
    for kind, scope, msg in findings:
        by_kind.setdefault(kind, []).append((scope, msg))
    for kind in sorted(by_kind):
        print(f"[{kind}]")
        for scope, msg in by_kind[kind]:
            print(f"  {scope}: {msg}")
        print()
    write_json({"checked_at": iso(), "findings": [
        {"kind": k, "scope": s, "message": msg} for k, s, msg in findings
    ]}, root / "state" / "doctor.json")


LOCAL_CLI = r"(?:^|[\s;&|(])\./[A-Za-z0-9._-]+"

BOOT_HINT = re.compile(
    r"\bnpm (?:run )?(?:start|dev|serve)\b|\byarn (?:start|dev)\b|\bpnpm (?:run )?(?:start|dev)\b"
    r"|\bng serve\b|\bnext dev\b|\bvite\b|\bflutter run\b"
    r"|\bmanage\.py runserver\b|\buvicorn\b|\bgunicorn\b|\bflask run\b"
    r"|\bdocker[- ]compose up\b|\bmake (?:run|dev|start|serve|up)\b"
    r"|\bgo run\b|\bcargo run\b"
    rf"|{LOCAL_CLI} (?:dev|run|start|serve|up)\b", re.I)

TEST_HINT = re.compile(
    r"\bnpm (?:run )?test\b|\byarn test\b|\bpnpm (?:run )?test\b"
    r"|\bpytest\b|\bjest\b|\bvitest\b|\bplaywright test\b|\bcypress run\b"
    r"|\bgo test\b|\bcargo test\b|\bmanage\.py test\b"
    rf"|{LOCAL_CLI} (?:test|e2e|check)\b", re.I)


def cmd_digest(args):
    root = find_root(args.cwd, getattr(args, "cluster", None))
    if root is None:
        return

    sid = args.session_id
    marker = root / "state" / "processed" / f"{sid}.done"
    if marker.exists():
        return

    tpath = Path(args.transcript)
    if not tpath.exists():
        return

    msgs = [m for m in T.load_transcript(tpath) if not T.is_meta(m)]
    if len(msgs) < 6:
        return

    m = manifest(root)
    repo_by_path = {}
    for r, p in repo_paths(root, m):
        repo_by_path[str(p).replace("\\", "/").lower()] = r["name"]

    def repo_of(path_str):
        s = str(path_str).replace("\\", "/").lower()
        for rp, name in repo_by_path.items():
            if s.startswith(rp):
                return name
        return None

    commands, errors, files_read, files_edited, repos_touched = [], [], [], [], set()
    user_turns = []
    boot_attempts, test_attempts = [], []
    searches = []

    for msg in msgs:
        role = T.role_of(msg)
        if role == "user":
            txt = T.extract_text(msg).strip()
            if txt and not txt.startswith("<"):
                user_turns.append(txt[:600])
            for res in T.tool_results(msg):
                if res["is_error"]:
                    errors.append(res["text"][:400])
        elif role == "assistant":
            for tu in T.tool_uses(msg):
                nm, inp = tu["name"], tu["input"]
                if nm in ("Bash", "PowerShell"):
                    cmd = str(inp.get("command", ""))[:400]
                    if cmd:
                        commands.append(cmd)
                        if BOOT_HINT.search(cmd):
                            boot_attempts.append(cmd)
                        if TEST_HINT.search(cmd):
                            test_attempts.append(cmd)
                elif nm in ("Read", "NotebookEdit"):
                    fp = inp.get("file_path") or inp.get("notebook_path")
                    if fp:
                        files_read.append(str(fp))
                        r = repo_of(fp)
                        if r:
                            repos_touched.add(r)
                elif nm in ("Edit", "Write"):
                    fp = inp.get("file_path")
                    if fp:
                        files_edited.append(str(fp))
                        r = repo_of(fp)
                        if r:
                            repos_touched.add(r)
                elif nm in ("Grep", "Glob"):
                    searches.append({
                        "pattern": str(inp.get("pattern", ""))[:200],
                        "path": str(inp.get("path", "")),
                    })

    def dedup_count(items):
        c = {}
        for i in items:
            c[i] = c.get(i, 0) + 1
        return sorted(c.items(), key=lambda kv: -kv[1])

    digest = {
        "session_id": sid,
        "cwd": args.cwd,
        "at": iso(),
        "messages": len(msgs),
        "repos_touched": sorted(repos_touched),
        "user_turns": user_turns[:40],
        "commands": [c for c, _ in dedup_count(commands)][:60],
        "repeated_commands": [{"command": c, "n": n} for c, n in dedup_count(commands) if n > 1][:20],
        "boot_attempts": sorted(set(boot_attempts))[:15],
        "test_attempts": sorted(set(test_attempts))[:15],
        "repeated_errors": [{"error": e, "n": n} for e, n in dedup_count(errors) if n > 1][:15],
        "errors": [e for e, _ in dedup_count(errors)][:20],
        "files_read": len(set(files_read)),
        "files_read_sample": sorted(set(files_read))[:40],
        "files_edited": sorted(set(files_edited))[:40],
        "cross_repo_searches": [s for s in searches if s.get("path") and repo_of(s["path"]) is None][:15],
    }
    write_json(digest, root / "state" / "sessions" / f"{sid}.json")
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(iso(), encoding="utf-8")


def gather_batch(root, m):
    cfg = m.get("garden") or {}
    lookback = int(cfg.get("lookback_days", 14))
    cutoff = now() - timedelta(days=lookback)
    sessions = []
    for f in sorted((root / "state" / "sessions").glob("*.json")):
        d = read_json(f)
        if not d:
            continue
        try:
            at = datetime.fromisoformat(d.get("at", ""))
        except ValueError:
            continue
        if at >= cutoff:
            sessions.append(d)
    return sessions, cfg


def build_garden_prompt(root, m, sessions, doctor, gaps):
    taxonomy = (SKILL_DIR / "references" / "signals.md").read_text(encoding="utf-8")
    cfg = m.get("garden") or {}
    repos = ", ".join(f"{r['name']} ({r.get('role')})" for r in m.get("repos", []))

    sess_txt = json.dumps(sessions, ensure_ascii=False, indent=1)
    if len(sess_txt) > 90000:
        sess_txt = sess_txt[:90000] + "\n... [truncated]"

    return f"""You maintain the agent harness for a cluster of related git repos.

CLUSTER: {m.get('name')}
REPOS: {repos}
HARNESS ROOT: {root}

Below are (A) the signal taxonomy you must apply, (B) raw digests of recent Claude Code sessions in this
cluster, (C) mechanical drift findings, and (D) open rubric gaps.

Your job: find places where a session shows the agent STUMBLING, and name the harness artifact that would
have prevented it. Do not give generic advice. Every proposal must cite specific evidence from the digests.

HARD RULES:
- At most {cfg.get('max_proposals_per_run', 5)} proposals.
- A signal must appear at least {cfg.get('min_occurrences', 2)} times, unless it is a repeated tool error
  or an explicit user correction (those count from one occurrence).
- If you cannot point at the specific command, error, or user turn that provoked a proposal, DO NOT EMIT IT.
- Prefer an enforceable artifact (a lint) over prose (a paragraph) whenever the rule is mechanizable.
- One proposal, one gap. Never bundle.
- Repeated shell commands that should become a CLI subcommand are NOT your job. Skip them.
- If the sessions show no real harness gap, return an empty list. That is a correct and expected answer.
- `content` MUST be the complete, ready-to-write file body when apply_mode is "create", or the exact
  block to append when it is "append". If you cannot write that content concretely, set apply_mode to
  "manual" and leave content empty. An empty patch with apply_mode "create" is a bug, not a proposal.

=== A. SIGNAL TAXONOMY ===
{taxonomy}

=== B. SESSION DIGESTS ({len(sessions)}) ===
{sess_txt}

=== C. DRIFT FINDINGS ===
{json.dumps(doctor, ensure_ascii=False, indent=1)[:8000]}

=== D. RUBRIC GAPS ===
{json.dumps(gaps[:15], ensure_ascii=False, indent=1)[:6000]}

OUTPUT: return ONLY a single JSON object, no prose, no code fences.
{{
  "proposals": [
    {{
      "id": "kebab-case-slug",
      "title": "one line",
      "kind": "init-script|golden-principle|invariant|doc|contract|plan|map|work-spec",
      "target_repo": "<repo name from the cluster, or __cluster__ for the harness root>",
      "target_path": "<path relative to that repo or to the harness root>",
      "rubric_dim": 3,
      "apply_mode": "create|append|manual",
      "evidence": "quote the exact commands/errors/user turns from the digests that provoked this",
      "evidence_sessions": ["session-id"],
      "occurrences": 2,
      "rationale": "why this artifact closes the gap",
      "content": "the exact file content (create) or the exact block to append (append). Empty for manual."
    }}
  ]
}}
"""


def parse_proposals(output):
    if not output or not output.strip():
        return []
    out = output.strip()
    cands = []
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", out, re.DOTALL)
    if fenced:
        cands.append(fenced.group(1))
    cands.append(out)
    obj = re.search(r"\{[\s\S]*\}", out)
    if obj:
        cands.append(obj.group(0))
    for raw in cands:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return [p for p in (data.get("proposals") or []) if isinstance(p, dict) and p.get("id")]
    return []


def save_proposal(root, p):
    pid = slug(p["id"])
    dest = root / "proposals" / "_pending" / f"{pid}.md"
    if dest.exists():
        dest = root / "proposals" / "_pending" / f"{pid}-{now().strftime('%Y%m%d-%H%M%S')}.md"

    mode = p.get("apply_mode", "manual")
    if mode in ("create", "append") and not str(p.get("content", "")).strip():
        mode = "manual"

    fm = {
        "id": pid,
        "title": p.get("title", ""),
        "kind": p.get("kind", "doc"),
        "target_repo": p.get("target_repo", "__cluster__"),
        "target_path": p.get("target_path", ""),
        "rubric_dim": p.get("rubric_dim"),
        "apply_mode": mode,
        "evidence_sessions": p.get("evidence_sessions") or [],
        "occurrences": p.get("occurrences", 1),
        "created_at": iso(),
    }
    body = [
        "---",
        yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip(),
        "---",
        "",
        f"# {p.get('title', pid)}",
        "",
        "## Evidence",
        "",
        str(p.get("evidence", "(none given)")),
        "",
        "## Why this closes the gap",
        "",
        str(p.get("rationale", "")),
        "",
        "## Patch",
        "",
        f"Target: `{p.get('target_repo')}` -> `{p.get('target_path')}` (mode: {fm['apply_mode']})",
        "",
        "```",
        str(p.get("content", "")),
        "```",
        "",
    ]
    dest.write_text("\n".join(body), encoding="utf-8")
    return dest


def cmd_garden(args):
    root = need_root(args)
    m = manifest(root)
    sessions, cfg = gather_batch(root, m)

    if len(sessions) < int(cfg.get("min_sessions", 3)) and not args.force:
        print(f"Only {len(sessions)} session digest(s) in the lookback window; need {cfg.get('min_sessions', 3)}.")
        print("A single session is noise. Use --force to run anyway.")
        return

    doctor = read_json(root / "state" / "doctor.json", {"findings": []})
    gaps = (read_json(root / "state" / "gaps.json", {}) or {}).get("gaps", [])
    prompt = build_garden_prompt(root, m, sessions, doctor, gaps)

    if not args.headless:
        out = root / "state" / "garden-batch.md"
        out.write_text(prompt, encoding="utf-8")
        print(f"Gardening batch prepared: {out}")
        print(f"{len(sessions)} session(s), {len(doctor.get('findings', []))} drift finding(s), {len(gaps)} rubric gap(s).")
        print()
        print("Read that file, apply the taxonomy yourself, and write each proposal with:")
        print("  python harness.py propose --file <proposal.json>")
        print("Or run with --headless to have `claude -p` do it.")
        return

    model = cfg.get("model", "claude-haiku-4-5")
    env = os.environ.copy()
    env["HARNESS_CHILD"] = "1"
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--model", model],
            capture_output=True, text=True, timeout=int(cfg.get("timeout_seconds", 300)),
            env=env, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        print("claude -p timed out", file=sys.stderr)
        return
    except FileNotFoundError:
        print("claude CLI not found in PATH", file=sys.stderr)
        return
    if proc.returncode != 0:
        print(f"claude -p failed rc={proc.returncode}: {proc.stderr[:500]}", file=sys.stderr)
        return

    props = parse_proposals(proc.stdout)
    if not props:
        print("No proposals. The harness has no gap the sessions can prove.")
        return
    for p in props[: int(cfg.get("max_proposals_per_run", 5))]:
        print(f"proposal: {save_proposal(root, p)}")


def cmd_propose(args):
    root = need_root(args)
    data = read_json(args.file)
    if not data:
        print(f"Cannot read {args.file}", file=sys.stderr)
        sys.exit(1)
    items = data.get("proposals") if isinstance(data, dict) else data
    if isinstance(items, dict):
        items = [items]
    for p in items or []:
        print(f"proposal: {save_proposal(root, p)}")


def read_proposal(path):
    txt = Path(path).read_text(encoding="utf-8")
    mfm = re.match(r"^---\n(.*?)\n---\n", txt, re.DOTALL)
    fm = yaml.safe_load(mfm.group(1)) if mfm else {}
    patch = ""
    pm = re.search(r"## Patch\n.*?\n```\n(.*?)\n```", txt, re.DOTALL)
    if pm:
        patch = pm.group(1)
    return fm or {}, patch, txt


def cmd_review(args):
    root = need_root(args)
    pend = sorted((root / "proposals" / "_pending").glob("*.md"))
    if not pend:
        print("No pending proposals.")
        return
    print(f"{len(pend)} pending proposal(s):\n")
    for f in pend:
        fm, _, _ = read_proposal(f)
        print(f"  {f.stem}")
        print(f"    {fm.get('title', '')}")
        print(f"    kind={fm.get('kind')}  dim={fm.get('rubric_dim')}  x{fm.get('occurrences')}  -> {fm.get('target_repo')}/{fm.get('target_path')}")
        print(f"    {f}")
        print()
    print("Read one, then: python harness.py apply <id>   |   python harness.py reject <id>")


def resolve_target(root, m, fm):
    tr = fm.get("target_repo") or "__cluster__"
    if tr == "__cluster__":
        return root, None
    for r, p in repo_paths(root, m):
        if r["name"] == tr:
            return p, r
    return None, None


def cmd_apply(args):
    root = need_root(args)
    m = manifest(root)
    src = root / "proposals" / "_pending" / f"{args.id}.md"
    if not src.exists():
        print(f"No pending proposal '{args.id}'", file=sys.stderr)
        sys.exit(1)
    fm, patch, _ = read_proposal(src)

    base, _r = resolve_target(root, m, fm)
    if base is None:
        print(f"Proposal targets repo '{fm.get('target_repo')}' which is not in the cluster", file=sys.stderr)
        sys.exit(1)

    mode = fm.get("apply_mode", "manual")
    target = base / fm.get("target_path", "")

    if mode == "manual" or not patch.strip():
        why = "mode=manual" if mode == "manual" else f"mode={mode} but the patch is empty"
        print(f"Proposal '{args.id}': {why}. Nothing written.")
        print(f"Read it and make the change yourself: {src}")
        print(f"Target: {target}")
        return

    branch = args.branch or f"harness/{args.id}"
    if is_git_repo(base):
        cur = git(base, "rev-parse", "--abbrev-ref", "HEAD")
        if git(base, "status", "--porcelain"):
            print(f"{base} has uncommitted changes. Commit or stash first; refusing to branch.", file=sys.stderr)
            sys.exit(1)
        if cur != branch:
            if git(base, "rev-parse", "--verify", branch) is None:
                git(base, "checkout", "-b", branch)
            else:
                git(base, "checkout", branch)
        print(f"On branch {branch} in {base}")

    target.parent.mkdir(parents=True, exist_ok=True)
    if mode == "append" and target.exists():
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n" + patch.rstrip() + "\n")
    else:
        target.write_text(patch.rstrip() + "\n", encoding="utf-8")
    print(f"{'Appended to' if mode == 'append' else 'Wrote'} {target}")

    dest = root / "proposals" / "applied" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dest)
    print(f"Proposal archived: {dest}")
    print()
    print("Nothing was pushed or merged. Review the diff, then commit and open a PR yourself.")


def cmd_reject(args):
    root = need_root(args)
    src = root / "proposals" / "_pending" / f"{args.id}.md"
    if not src.exists():
        print(f"No pending proposal '{args.id}'", file=sys.stderr)
        sys.exit(1)
    dest = root / "proposals" / "rejected" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dest)
    print(f"Rejected: {dest}")


def cmd_plan(args):
    root = need_root(args)
    m = manifest(root)
    active = root / "plans" / "active"
    active.mkdir(parents=True, exist_ok=True)

    if args.action == "create":
        if not args.name:
            print("plan create needs --name", file=sys.stderr)
            sys.exit(1)
        pid = slug(args.name)
        f = active / f"{pid}.yaml"
        if f.exists():
            print(f"Plan already exists: {f}", file=sys.stderr)
            sys.exit(1)
        plan = {
            "id": pid,
            "goal": args.goal or args.name,
            "created_at": iso(),
            "repos": [
                {"repo": r["name"], "branch": f"feat/{pid}", "order": i + 1, "depends_on": [], "status": "pending"}
                for i, r in enumerate(m.get("repos", [])) if r["name"] in (args.repos or "").split(",")
            ],
            "steps": [],
            "decisions": [],
        }
        write_yaml(plan, f)
        print(f"Created {f}")
        print("Edit it: set the merge order, depends_on, and the steps. Order matters: an owner repo merges before its consumers.")
        return

    if args.action == "status":
        scan = load_scan(root, refresh=True)
        plans = sorted(active.glob("*.yaml"))
        if not plans:
            print("No active plans.")
            return
        for f in plans:
            plan = read_yaml(f) or {}
            print(f"\n# {plan.get('id')}: {plan.get('goal')}")
            entries = sorted(plan.get("repos", []), key=lambda e: e.get("order", 99))
            for e in entries:
                rn = e.get("repo")
                rec = scan["repos"].get(rn, {})
                actual = rec.get("git", {}).get("branch") if not rec.get("missing_on_disk") else "(absent)"
                want = e.get("branch")
                dirty = " *dirty" if rec.get("git", {}).get("dirty") else ""
                mark = "ok " if actual == want else ("PLAN" if e.get("status") in {"pending", "todo"} else "DRIFT")
                dep = f" after={','.join(e.get('depends_on') or [])}" if e.get("depends_on") else ""
                print(f"  [{mark}] {e.get('order')}. {rn:<28} want={want}  actual={actual}{dirty}{dep}  status={e.get('status')}")
            if plan.get("decisions"):
                print("  decisions:")
                for d in plan["decisions"]:
                    print(f"    - {d}")
        return

    if args.action == "decide":
        f = active / f"{slug(args.name)}.yaml"
        plan = read_yaml(f)
        if not plan:
            print(f"No such plan: {f}", file=sys.stderr)
            sys.exit(1)
        plan.setdefault("decisions", []).append(f"{iso()}: {args.text}")
        write_yaml(plan, f)
        print(f"Logged decision in {f}")
        return

    if args.action == "complete":
        f = active / f"{slug(args.name)}.yaml"
        if not f.exists():
            print(f"No such plan: {f}", file=sys.stderr)
            sys.exit(1)
        dest = root / "plans" / "completed" / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        f.rename(dest)
        print(f"Completed: {dest}")


def cmd_where(args):
    root = find_root(getattr(args, "root", None), getattr(args, "cluster", None))
    if root is None:
        print("No harness for this location.")
        reg = load_registry()
        if reg.get("clusters"):
            print("\nKnown clusters:")
            for c in reg["clusters"]:
                print(f"  {c['name']:<24} {c['root']}")
        sys.exit(1)
    m = manifest(root)
    print(f"cluster: {m.get('name')}")
    print(f"root:    {root}")
    print(f"repos:   {len(m.get('repos', []))}")


def main():
    ap = argparse.ArgumentParser(prog="harness.py", description="Analyze, build and maintain an agent harness for a cluster of repos")
    ap.add_argument("--root", help="harness root (default: discover from cwd or registry)")
    ap.add_argument("--cluster", help="cluster name (resolves via the registry)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="discover repos and create a harness root")
    p.add_argument("--workspace", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--include", help="comma-separated regexes; only matching repo names")
    p.add_argument("--exclude", help="comma-separated regexes")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("scan", help="snapshot git state and harness artifacts per repo")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("audit", help="score the cluster against the rubric and report the top gaps")
    p.add_argument("--top", type=int, default=5)
    p.add_argument("--no-scan", action="store_true", help="reuse the last scan instead of rescanning")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("doctor", help="find drift: dead links, absent repos, unverified seams, plan-vs-git mismatch")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("digest", help="record raw facts from a session transcript (no model; called by the SessionEnd hook)")
    p.add_argument("--transcript", required=True)
    p.add_argument("--cwd", required=True)
    p.add_argument("--session-id", required=True)
    p.set_defaults(func=cmd_digest)

    p = sub.add_parser("garden", help="turn session digests + drift into harness proposals")
    p.add_argument("--headless", action="store_true", help="let `claude -p` write the proposals (for cron)")
    p.add_argument("--force", action="store_true", help="run even with too few sessions")
    p.set_defaults(func=cmd_garden)

    p = sub.add_parser("propose", help="save proposals from a JSON file")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_propose)

    p = sub.add_parser("review", help="list pending proposals")
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("apply", help="apply a proposal onto a branch in the target repo (never pushes)")
    p.add_argument("id")
    p.add_argument("--branch")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("reject", help="archive a proposal without applying it")
    p.add_argument("id")
    p.set_defaults(func=cmd_reject)

    p = sub.add_parser("plan", help="cross-repo execution plans")
    p.add_argument("action", choices=["create", "status", "decide", "complete"])
    p.add_argument("--name")
    p.add_argument("--goal")
    p.add_argument("--repos", help="comma-separated repo names")
    p.add_argument("--text", help="decision text (for `decide`)")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("where", help="show which cluster this directory belongs to")
    p.set_defaults(func=cmd_where)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
