#!/usr/bin/env python3
"""How far this machine, and the harness around the current directory, are behind the latest evo-agents.

Stdlib only, Python 3.9+.

  check.py                  a readable report
  check.py --json           the same as JSON, read by the evo-agents-updater agent
  check.py --notice         one line for a SessionStart hook, printed only when something is behind;
                            the release lookup is cached for 12 hours and any failure prints nothing
  check.py --harness DIR    the harness whose CI pins to read (default: walk up from the current directory)
  check.py --all-harnesses  also every harness in this machine's harness registry

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
CACHE = Path.home() / ".cache" / "evo-agents-update" / "latest.json"
CACHE_SECONDS = 12 * 3600
HTTP_TIMEOUT = 4
PIN_RE = re.compile(r"evo-ak(?:\[[^\]]*\])?\s*==\s*([0-9][0-9A-Za-z.+-]*)")
REGISTRIES = (Path.home() / ".evo" / "harness" / "registry.json", Path.home() / ".claude" / "harness" / "registry.json")


def vkey(version: str | None) -> tuple:
    if not version:
        return ()
    return tuple(int(p) for p in re.findall(r"\d+", version.split("+")[0])[:3])


def older(version: str | None, latest: str | None) -> bool:
    return bool(version and latest and vkey(version) < vkey(latest))


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 20) -> str | None:
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout if out.returncode == 0 else None


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:
        return json.load(resp)


def latest_versions(use_cache: bool) -> dict:
    cached = None
    try:
        cached = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        pass
    if use_cache and cached and time.time() - cached.get("fetched_at", 0) < CACHE_SECONDS:
        return {**cached, "source": "cache"}
    try:
        found = {
            PACKAGE: fetch_json(PYPI_URL)["info"]["version"],
            "plugins": {name: fetch_json(PLUGIN_URL.format(name=name))["version"] for name in PLUGINS},
            "fetched_at": time.time(),
        }
    except Exception as exc:  # network, JSON or key errors all mean "unknown"
        if cached:
            return {**cached, "source": "cache", "error": f"lookup failed, using the cache: {exc}"}
        return {PACKAGE: None, "plugins": {}, "source": None, "error": f"lookup failed: {exc}"}
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(found))
    except OSError:
        pass
    return {**found, "source": "network"}


def uv_receipt() -> Path | None:
    tool_dir = os.environ.get("UV_TOOL_DIR")
    if not tool_dir and shutil.which("uv"):
        tool_dir = (run(["uv", "tool", "dir"], timeout=5) or "").strip()
    if not tool_dir:
        tool_dir = str(Path.home() / ".local" / "share" / "uv" / "tools")
    receipt = Path(tool_dir) / PACKAGE / "uv-receipt.toml"
    return receipt if receipt.is_file() else None


def cli_state(latest: str | None) -> dict:
    exe = shutil.which("evo-agents")
    state = {"path": exe, "version": None, "installer": None, "extras": [], "requirement": None, "behind": False}
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
    state["requirement"] = f"{PACKAGE}{extras}=={latest}" if latest else None
    state["behind"] = older(state["version"], latest)
    return state


def installed_plugins() -> dict[str, str]:
    path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    try:
        data = json.loads(path.read_text()).get("plugins", {})
        return {pid: entries[0].get("version") for pid, entries in data.items() if entries}
    except (OSError, ValueError, AttributeError, IndexError):
        pass
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


def worker_state(cli_version: str | None, latest: str | None) -> dict:
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
    target = max([v for v in (cli_version, latest) if v], key=vkey, default=None)
    return {
        "installed": True,
        "name": data.get("name"),
        "daemon_pid": data.get("daemon_pid"),
        "daemon_version": daemon_version,
        "status": hub.get("status"),
        "held_runs": held,
        "drained": bool(hub.get("drained_at")),
        "hub_error": data.get("hub_error"),
        "behind": bool(data.get("daemon_pid")) and older(daemon_version, target),
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
    if report["cli"]["behind"]:
        items.append(f"CLI {report['cli']['version']}")
    for row in report["plugins"]:
        if row["behind"]:
            items.append(f"plugin {row['id'].split('@')[0]} {row['version']}")
    if report.get("worker", {}).get("behind"):
        items.append(f"worker daemon {report['worker']['daemon_version']}")
    for h in report["harnesses"]:
        if h["behind"]:
            versions = sorted({p["version"] for p in h["pins"] if older(p["version"], report["latest"][PACKAGE])})
            items.append(f"CI pin of {h['name']} {', '.join(versions)}")
    return items


def build(args) -> dict:
    latest = latest_versions(use_cache=args.notice)
    newest = latest.get(PACKAGE)
    cli = cli_state(newest)
    report = {"latest": latest, "cli": cli, "plugins": plugin_state(latest.get("plugins", {}))}
    if not args.notice:
        report["worker"] = worker_state(cli["version"], newest)
    roots: list[Path] = []
    here = Path(args.harness).resolve() if args.harness else find_harness(Path.cwd().resolve())
    if here:
        roots.append(here)
    if args.all_harnesses:
        roots += [r for r in registry_roots() if r.resolve() not in {x.resolve() for x in roots}]
    report["harnesses"] = [harness_state(r, newest) for r in roots]
    report["behind"] = behind_list(report)
    return report


def print_report(report: dict) -> None:
    latest = report["latest"]
    print(f"latest {PACKAGE}: {latest.get(PACKAGE)} (plugins {latest.get('plugins')}, from {latest.get('source')})")
    if latest.get("error"):
        print(f"  {latest['error']}")
    cli = report["cli"]
    print(f"CLI: {cli['version']} via {cli['installer']} at {cli['path']}" + ("  BEHIND" if cli["behind"] else ""))
    for row in report["plugins"]:
        print(f"plugin {row['id']}: {row['version']} (latest {row['latest']})" + ("  BEHIND" if row["behind"] else ""))
    w = report.get("worker", {})
    if w.get("installed"):
        print(f"worker {w['name']}: daemon {w['daemon_version']} pid {w['daemon_pid']}, {w['status']}, "
              f"{w['held_runs']} run(s) held" + ("  BEHIND" if w["behind"] else ""))
    for h in report["harnesses"]:
        pins = ", ".join(f"{p['file']}:{p['line']} {p['version']}" for p in h["pins"]) or "no evo-ak pin"
        print(f"harness {h['name']} ({h['ref']}): {pins}" + ("  BEHIND" if h["behind"] else ""))
    print("behind: " + ("; ".join(report["behind"]) if report["behind"] else "nothing"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--notice", action="store_true")
    parser.add_argument("--harness")
    parser.add_argument("--all-harnesses", action="store_true")
    args = parser.parse_args()

    if args.notice:
        if os.environ.get("EVO_RUN_ID") or os.environ.get("EVO_AGENTS_UPDATE_NOTICE") == "0":
            return 0
        try:
            report = build(args)
        except Exception:
            return 0
        if report["behind"]:
            print(f"evo-agents update: {PACKAGE} {report['latest'][PACKAGE]} is out; behind: "
                  f"{'; '.join(report['behind'])}. Use the update-evo-agents skill, which runs the "
                  "evo-agents-updater agent in the background.")
        return 0

    report = build(args)
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
