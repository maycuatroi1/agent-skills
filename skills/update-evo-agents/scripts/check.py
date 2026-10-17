#!/usr/bin/env python3
"""How far this machine, and the harness around the current directory, are behind evo-agents.

The CLI and the worker daemon follow the nightly tag of main, the plugins follow main, the CI pins
follow the latest PyPI release. The plugins' hooks and MCP servers run `uvx --offline --from
evo-ak==X`, so each such X must be in uv's cache or they do nothing; the skills follow the hub
(`evo-agents hub skills sync`); the hub's own version is reported, never updated. Stdlib only,
Python 3.9+.

  check.py                  a readable report
  check.py --json           the same as JSON, read by the evo-agents-updater agent
  check.py --notice         one line for a SessionStart hook, printed only when something is behind;
                            the release and nightly lookups are cached for 12 hours and any failure
                            prints nothing
  check.py --harness DIR    a harness whose CI pins to read; repeat it for several
                            (default: walk up from the current directory)
  check.py --all-harnesses  also every harness in this machine's harness registry
  check.py --local          this machine only: no harness and no CI pin

The notice stays silent inside an evo-agents worker run (EVO_RUN_ID is set) and when
EVO_AGENTS_UPDATE_NOTICE=0.
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
import urllib.request
from pathlib import Path

PACKAGE = "evo-ak"
PLUGINS = ("evo-hub", "evo-kg")
MARKETPLACE = "evo-agents"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE}/json"
PLUGIN_URL = "https://raw.githubusercontent.com/maycuatroi1/evo-agents/main/plugins/{name}/.claude-plugin/plugin.json"
REPO_URL = "https://github.com/maycuatroi1/evo-agents"
NIGHTLY = "nightly"
NIGHTLY_API = f"https://api.github.com/repos/maycuatroi1/evo-agents/git/ref/tags/{NIGHTLY}"
CACHE = Path.home() / ".cache" / "evo-agents-update" / "latest.json"
NIGHTLY_CACHE = CACHE.with_name("nightly.json")
CACHE_SECONDS = 12 * 3600
HTTP_TIMEOUT = 4
PIN_RE = re.compile(r"evo-ak(?:\[[^\]]*\])?\s*==\s*([0-9][0-9A-Za-z.+-]*)")
REGISTRIES = (Path.home() / ".evo" / "harness" / "registry.json", Path.home() / ".claude" / "harness" / "registry.json")
HUB_CONFIG = Path.home() / ".evo" / "hub" / "config.json"  # the hub URL and login; the token is in another file
PLUGIN_FILES = ("hooks/hooks.json", ".mcp.json", ".claude-plugin/plugin.json")  # where a plugin runs evo-ak
SKILL_STATES = ("current", "unmanaged")  # a skill sync leaves these alone without --adopt


def vkey(version: str | None) -> tuple:
    if not version:
        return ()
    return tuple(int(p) for p in re.findall(r"\d+", version.split("+")[0])[:3])


def older(version: str | None, latest: str | None) -> bool:
    return bool(version and latest and vkey(version) < vkey(latest))


def short(commit: str | None) -> str | None:
    return commit[:7] if commit else None


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 20, env: dict | None = None) -> str | None:
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                             env={**os.environ, **env} if env else None)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout if out.returncode == 0 else None


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:
        return json.load(resp)


def cached_lookup(path: Path, use_cache: bool, lookup, unknown: dict) -> dict:
    cached = None
    try:
        cached = json.loads(path.read_text())
    except (OSError, ValueError):
        pass
    if use_cache and cached and time.time() - cached.get("fetched_at", 0) < CACHE_SECONDS:
        return {**cached, "source": "cache"}
    try:
        found = {**lookup(), "fetched_at": time.time()}
    except Exception as exc:  # network, JSON, key errors and a missing tag all mean "unknown"
        if cached:
            return {**cached, "source": "cache", "error": f"lookup failed, using the cache: {exc}"}
        return {**unknown, "source": None, "error": f"lookup failed: {exc}"}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(found))
    except OSError:
        pass
    return {**found, "source": "network"}


def latest_versions(use_cache: bool) -> dict:
    return cached_lookup(CACHE, use_cache, lambda: {
        PACKAGE: fetch_json(PYPI_URL)["info"]["version"],
        "plugins": {name: fetch_json(PLUGIN_URL.format(name=name))["version"] for name in PLUGINS},
    }, {PACKAGE: None, "plugins": {}})


def nightly_commit() -> dict:
    ref = f"refs/tags/{NIGHTLY}"
    # An annotated tag lists its tag object; the peeled ^{} line is the commit.
    out = run(["git", "ls-remote", REPO_URL, ref, ref + "^{}"], timeout=8, env={"GIT_TERMINAL_PROMPT": "0"})
    if out is not None:
        shas = {name: sha for sha, name in (line.split("\t", 1) for line in out.splitlines() if "\t" in line)}
        commit = shas.get(ref + "^{}") or shas.get(ref)
        if not commit:
            raise LookupError(f"no tag {NIGHTLY} on {REPO_URL}")
        return {"tag": NIGHTLY, "commit": commit}
    obj = fetch_json(NIGHTLY_API)["object"]  # git missing or failed; a missing tag is a 404
    if obj.get("type") == "tag":
        obj = fetch_json(obj["url"])["object"]
    return {"tag": NIGHTLY, "commit": obj["sha"]}


def nightly_state(use_cache: bool) -> dict:
    return cached_lookup(NIGHTLY_CACHE, use_cache, nightly_commit, {"tag": NIGHTLY, "commit": None})


def uv_receipt() -> Path | None:
    tool_dir = os.environ.get("UV_TOOL_DIR")
    if not tool_dir and shutil.which("uv"):
        tool_dir = (run(["uv", "tool", "dir"], timeout=5) or "").strip()
    if not tool_dir:
        tool_dir = str(Path.home() / ".local" / "share" / "uv" / "tools")
    receipt = Path(tool_dir) / PACKAGE / "uv-receipt.toml"
    return receipt if receipt.is_file() else None


def direct_url(receipt: Path | None, exe: str) -> dict | None:
    """direct_url.json of the installed evo-ak: {} when it came from an index (PyPI), None when not found."""
    if receipt:
        env = receipt.parent
        dists = sorted(env.glob("lib/python*/site-packages/evo_ak-*.dist-info")) or sorted(
            env.glob("Lib/site-packages/evo_ak-*.dist-info"))
        if not dists:
            return None
        try:
            return json.loads((dists[-1] / "direct_url.json").read_text())
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):
            return None
    try:  # pip: ask the Python that owns the script
        with open(exe) as f:
            shebang = f.readline()
    except (OSError, UnicodeDecodeError):
        return None
    if not shebang.startswith("#!"):
        return None
    out = run([*shebang[2:].split(), "-c", "import importlib.metadata as m; "
               f"print(m.distribution('{PACKAGE}').read_text('direct_url.json') or '{{}}')"], timeout=10)
    try:
        return json.loads(out) if out else None
    except ValueError:
        return None


def cli_state(nightly: str | None) -> dict:
    exe = shutil.which("evo-agents")
    state = {"path": exe, "version": None, "installer": None, "extras": [], "requirement": None, "behind": False,
             "source": None, "url": None, "commit": None, "requested_revision": None, "action": None}
    if not exe:
        state["error"] = "evo-agents is not on PATH"
        return state
    out = run([exe, "--version"], timeout=10) or ""
    state["version"] = out.split()[-1] if out.split() else None
    receipt = uv_receipt()
    if receipt:
        state["installer"] = "uv"
        match = re.search(r'name\s*=\s*"evo-ak"[^}]*?extras\s*=\s*\[([^\]]*)\]', receipt.read_text())
        if match:
            state["extras"] = re.findall(r'"([^"]+)"', match.group(1))
    else:
        state["installer"] = "pip"
    extras = f"[{','.join(state['extras'])}]" if state["extras"] else ""
    state["requirement"] = f"{PACKAGE}{extras} @ git+{REPO_URL}@{NIGHTLY}"
    direct = direct_url(receipt, exe)
    if isinstance(direct, dict):
        vcs = direct.get("vcs_info") or {}
        # pypi: from the index; git: a git install; local: an editable or local install, left alone.
        state["source"] = "git" if vcs else ("local" if direct else "pypi")
        state["url"] = direct.get("url")
        state["commit"] = vcs.get("commit_id")
        state["requested_revision"] = vcs.get("requested_revision")
    if nightly and state["source"] == "pypi":
        state["action"] = "switch to nightly"
    elif nightly and state["source"] == "git" and state["commit"] != nightly:
        state["action"] = "reinstall at nightly"
    state["behind"] = bool(state["action"])
    return state


def installed_plugin_entries() -> dict[str, dict]:
    path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    try:
        data = json.loads(path.read_text()).get("plugins", {})
        return {pid: entries[0] for pid, entries in data.items() if entries and isinstance(entries[0], dict)}
    except (OSError, ValueError, AttributeError, IndexError):
        return {}


def installed_plugins() -> dict[str, str]:
    entries = installed_plugin_entries()
    if entries:
        return {pid: entry.get("version") for pid, entry in entries.items()}
    out = run(["claude", "plugin", "list", "--json"], timeout=30)
    try:
        return {p["id"]: p.get("version") for p in json.loads(out or "[]")}
    except (ValueError, KeyError, TypeError):
        return {}


def plugin_state(latest: dict) -> list[dict]:
    installed = installed_plugins()
    rows = []
    for name in PLUGINS:
        pid = f"{name}@{MARKETPLACE}"
        if pid not in installed:
            continue
        version, newest = installed[pid], latest.get(name)
        rows.append({"id": pid, "version": version, "latest": newest, "behind": older(version, newest)})
    return rows


def uv_cached(version: str) -> bool:
    """Whether `uvx --offline --from evo-ak==version` starts, as a plugin's hook runs it."""
    if not shutil.which("uvx"):
        return False
    return run(["uvx", "--offline", "--from", f"{PACKAGE}=={version}", "evo-agents", "--version"],
               timeout=30) is not None


def plugin_runtime_state() -> list[dict]:
    """Each evo-ak version an installed evo plugin pins in its hooks or MCP servers, and whether uv has it.

    The commands run `uvx --offline ... || true`: a version uv never downloaded makes every hook a silent
    no-op, and a plugin update moves the pin."""
    rows = []
    for pid, entry in installed_plugin_entries().items():
        if pid.split("@")[0] not in PLUGINS or not entry.get("installPath"):
            continue
        root, pins = Path(entry["installPath"]), set()
        for rel in PLUGIN_FILES:
            try:
                pins.update(PIN_RE.findall((root / rel).read_text()))
            except OSError:
                continue
        for version in sorted(pins, key=vkey):
            cached = uv_cached(version)
            rows.append({"plugin": pid, "pin": version, "cached": cached, "behind": not cached})
    return rows


def hub_state(latest: str | None, cli_version: str | None) -> dict:
    """The hub this machine signed in to, by its URL and login (never the token), and the version it runs."""
    try:
        config = json.loads(HUB_CONFIG.read_text())
        url, login = config["url"].rstrip("/"), config.get("login")
    except (OSError, ValueError, KeyError, AttributeError, TypeError):
        return {"signed_in": False}
    state = {"signed_in": True, "url": url, "login": login, "version": None, "schema": None}
    try:
        health = fetch_json(f"{url}/v1/health")
        state.update(version=health.get("version"), schema=health.get("schema"), status=health.get("status"))
    except Exception as exc:  # the hub down or unreachable: reported, never fatal
        state["error"] = f"health check failed: {exc}"
    # Never updated here: a deploy is for whoever runs the hub. A CLI older than its hub misses what the hub added.
    state["behind_release"] = older(state["version"], latest)
    state["cli_older"] = older(cli_version, state["version"])
    return state


def skills_state(hub: dict) -> dict:
    """What `evo-agents hub skills sync` would change: the skills to add or update, and the directories of the
    same name it leaves alone (unmanaged: --adopt replaces them, after a backup)."""
    exe = shutil.which("evo-agents")
    if not exe or not hub.get("signed_in"):
        return {"checked": False, "behind": False, "reason": "no evo-agents" if not exe else "not signed in"}
    out = run([exe, "hub", "skills", "sync", "--check", "--json"], timeout=60)
    try:
        data = json.loads(out or "")
    except ValueError:
        return {"checked": False, "behind": False, "reason": "skills sync --check printed no JSON"}
    changes, unmanaged = [], []
    for target in data.get("targets", []):
        where = target.get("project") or target.get("scope")
        for item in target.get("actions", []):
            row = {"name": item.get("name"), "runtime": target.get("runtime"), "where": where,
                   "action": item.get("action"), "detail": item.get("detail")}
            if item.get("action") == "unmanaged":
                unmanaged.append(row)
            elif item.get("action") not in SKILL_STATES:
                changes.append(row)
    return {"checked": True, "counts": data.get("counts", {}), "changes": changes, "unmanaged": unmanaged,
            "behind": bool(changes)}


def worker_state(cli: dict) -> dict:
    exe = shutil.which("evo-agents")
    out = run([exe, "worker", "status", "--json"], timeout=30) if exe else None
    if not out:
        return {"installed": False}
    try:
        data = json.loads(out)
    except ValueError:
        return {"installed": False, "error": "worker status printed no JSON"}
    hub = data.get("hub") or {}
    held = hub.get("held_runs")
    held = len(held) if isinstance(held, list) else (held or 0)
    daemon_version = hub.get("agent_version")
    return {
        "installed": True,
        "name": data.get("name"),
        "daemon_pid": data.get("daemon_pid"),
        "daemon_version": daemon_version,
        "status": hub.get("status"),
        "held_runs": held,
        "drained": bool(hub.get("drained_at")),
        "hub_error": data.get("hub_error"),
        # The daemon runs the CLI's code: behind when the CLI is, or when it still runs an older CLI.
        "behind": bool(data.get("daemon_pid")) and (cli["behind"] or older(daemon_version, cli["version"])),
    }


def find_harness(start: Path) -> Path | None:
    for directory in (start, *start.parents):
        if (directory / "harness.yaml").is_file():
            return directory
    return None


def upstream_ref(root: Path) -> str | None:
    out = run(["git", "-C", str(root), "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], timeout=5)
    return out.strip() if out else None


def harness_state(root: Path, latest: str | None) -> dict:
    name_match = re.search(r"^name:\s*(\S+)", (root / "harness.yaml").read_text(), re.M)
    ref = upstream_ref(root)
    files: dict[str, str] = {}
    if ref:
        listing = run(["git", "-C", str(root), "ls-tree", "--name-only", ref, ".github/workflows/"], timeout=5) or ""
        for rel in listing.split():
            if rel.endswith((".yml", ".yaml")):
                files[rel] = run(["git", "-C", str(root), "show", f"{ref}:{rel}"], timeout=5) or ""
    else:
        for path in sorted((root / ".github" / "workflows").glob("*.y*ml")):
            files[str(path.relative_to(root))] = path.read_text()
    pins = []
    for rel, text in files.items():
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in PIN_RE.finditer(line):
                pins.append({"file": rel, "line": lineno, "version": match.group(1)})
    return {
        "name": name_match.group(1) if name_match else root.name,
        "root": str(root),
        "ref": ref or "working tree",
        "pins": pins,
        "behind": any(older(p["version"], latest) for p in pins),
    }


def registry_roots() -> list[Path]:
    for path in REGISTRIES:
        try:
            clusters = json.loads(path.read_text()).get("clusters", [])
        except (OSError, ValueError, AttributeError):
            continue
        return [Path(c["root"]) for c in clusters if c.get("root") and Path(c["root"], "harness.yaml").is_file()]
    return []


def behind_list(report: dict) -> list[str]:
    items = []
    cli, latest = report["cli"], report["latest"][PACKAGE]
    if cli["behind"]:
        where = "PyPI" if cli["source"] == "pypi" else f"git {short(cli['commit'])}"
        items.append(f"CLI {cli['version']} ({where}) -> {NIGHTLY} {short(report['nightly']['commit'])}")
    for row in report["plugins"]:
        if row["behind"]:
            items.append(f"plugin {row['id'].split('@')[0]} {row['version']} -> {row['latest']}")
    if report.get("worker", {}).get("behind"):
        items.append(f"worker daemon {report['worker']['daemon_version']}")
    missing = sorted({row["pin"] for row in report.get("plugin_runtime", []) if row["behind"]}, key=vkey)
    if missing:
        items.append(f"uv cache lacks {', '.join(f'{PACKAGE}=={v}' for v in missing)}, which the plugins' hooks run")
    skills = report.get("skills", {})
    if skills.get("behind"):
        items.append(f"{len(skills['changes'])} skill change(s) from the hub")
    for h in report["harnesses"]:
        if h["behind"]:
            versions = sorted({p["version"] for p in h["pins"] if older(p["version"], latest)})
            items.append(f"CI pin of {h['name']} {', '.join(versions)} -> {latest}")
    return items


def harness_roots(args) -> list[Path]:
    roots = [Path(h).resolve() for h in args.harness]
    if not roots:
        here = find_harness(Path.cwd().resolve())
        roots = [here] if here else []
    if args.all_harnesses:
        roots += [r.resolve() for r in registry_roots()]
    if args.local:
        return []
    return list(dict.fromkeys(roots))


def build(args) -> dict:
    latest = latest_versions(use_cache=args.notice)
    nightly = nightly_state(use_cache=args.notice)
    newest = latest.get(PACKAGE)
    cli = cli_state(nightly.get("commit"))
    report = {"latest": latest, "nightly": nightly, "cli": cli, "plugins": plugin_state(latest.get("plugins", {})),
              "plugin_runtime": plugin_runtime_state()}
    if not args.notice:
        report["worker"] = worker_state(cli)
        report["hub"] = hub_state(newest, cli.get("version"))
        report["skills"] = skills_state(report["hub"])
    report["harnesses"] = [harness_state(r, newest) for r in harness_roots(args)]
    report["behind"] = behind_list(report)
    return report


def print_report(report: dict) -> None:
    latest = report["latest"]
    print(f"latest {PACKAGE}: {latest.get(PACKAGE)} (plugins {latest.get('plugins')}, from {latest.get('source')})")
    if latest.get("error"):
        print(f"  {latest['error']}")
    nightly = report["nightly"]
    print(f"{NIGHTLY}: {short(nightly.get('commit')) or 'unknown'}"
          + (f" (from {nightly['source']})" if nightly.get("source") else ""))
    if nightly.get("error"):
        print(f"  {nightly['error']}")
    cli = report["cli"]
    where = {"pypi": "PyPI", "git": f"git {short(cli['commit'])} (rev {cli['requested_revision']})",
             "local": f"local {cli['url']}"}.get(cli["source"], "an unknown source")
    print(f"CLI: {cli['version']} via {cli['installer']} at {cli['path']}, from {where}"
          + (f"  BEHIND: {cli['action']}" if cli["behind"] else ""))
    for row in report["plugins"]:
        print(f"plugin {row['id']}: {row['version']} (latest {row['latest']})" + ("  BEHIND" if row["behind"] else ""))
    w = report.get("worker", {})
    if w.get("installed"):
        print(f"worker {w['name']}: daemon {w['daemon_version']} pid {w['daemon_pid']}, {w['status']}, "
              f"{w['held_runs']} run(s) held" + ("  BEHIND" if w["behind"] else ""))
    for row in report.get("plugin_runtime", []):
        print(f"plugin {row['plugin']} runs {PACKAGE}=={row['pin']}: "
              + ("in the uv cache" if row["cached"] else "NOT in the uv cache, its hooks do nothing"))
    hub = report.get("hub", {})
    if hub.get("signed_in"):
        print(f"hub {hub['url']} as {hub['login']}: {hub.get('version') or 'unknown'}"
              + (f" ({hub['error']})" if hub.get("error") else "")
              + ("  older than the release (a deploy)" if hub.get("behind_release") else "")
              + ("  newer than the CLI" if hub.get("cli_older") else ""))
    elif "hub" in report:
        print("hub: not signed in (evo-agents hub login --url <hub>)")
    skills = report.get("skills", {})
    if skills.get("checked"):
        print(f"skills: {len(skills['changes'])} to sync, {len(skills['unmanaged'])} not the hub's (left alone)"
              + ("  BEHIND" if skills["behind"] else ""))
    elif skills:
        print(f"skills: not checked, {skills.get('reason')}")
    for h in report["harnesses"]:
        pins = ", ".join(f"{p['file']}:{p['line']} {p['version']}" for p in h["pins"]) or "no evo-ak pin"
        print(f"harness {h['name']} ({h['ref']}): {pins}" + ("  BEHIND" if h["behind"] else ""))
    print("behind: " + ("; ".join(report["behind"]) if report["behind"] else "nothing"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--notice", action="store_true")
    parser.add_argument("--harness", action="append", default=[], metavar="DIR")
    parser.add_argument("--all-harnesses", action="store_true")
    parser.add_argument("--local", action="store_true", help="this machine only: no harness, no CI pin")
    args = parser.parse_args()

    if args.notice:
        if os.environ.get("EVO_RUN_ID") or os.environ.get("EVO_AGENTS_UPDATE_NOTICE") == "0":
            return 0
        try:
            report = build(args)
        except Exception:
            return 0
        if report["behind"]:
            print(f"evo-agents update: {'; '.join(report['behind'])}. Use the update-evo-agents skill, "
                  "which runs the evo-agents-updater agent in the background.")
        return 0

    missing = [h for h in args.harness if not Path(h, "harness.yaml").is_file()]
    if missing:
        parser.error(f"no harness.yaml in {', '.join(missing)}")
    report = build(args)
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
