"""Tests of check.py without the network: a fake evo-agents on PATH, a uv tool directory, a worker home and harnesses
of their own, and the release and nightly lookups replaced.

python3 -m pytest -q skills/update-evo-agents/tests
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check  # noqa: E402

NIGHTLY = "a" * 40
OLD = "b" * 40
RELEASE = "0.22.1"

PINNED = """name: Harness Validate
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      # Pinned to a release (PyPI name evo-ak, command evo-agents): a schema change in evo-agents reaches
      # this harness through a reviewed bump.
      - name: Install evo-agents
        run: python -m pip install "evo-ak==0.16.1"
"""

FOLLOWS_NIGHTLY = """name: Harness Validate
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      # The evo-agents of the tag nightly. To lock this harness, install evo-ak==0.22.1 instead.
      - name: Install evo-agents
        run: python -m pip install "evo-ak @ git+https://github.com/maycuatroi1/evo-agents@nightly"
"""

FAKE_CLI = """#!/bin/sh
case "$1 $2" in
  "--version ") echo "evo-agents {version}" ;;
  "worker status") cat "{status}" ;;
  *) exit 1 ;;
esac
"""


def args(**overrides) -> argparse.Namespace:
    values = {"json": True, "notice": False, "harness": [], "all_harnesses": False, "local": True}
    return argparse.Namespace(**{**values, **overrides})


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def git(root: Path, *argv: str) -> None:
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "-c", "commit.gpgsign=false", *argv], check=True, capture_output=True)


def no_network(*_args, **_kwargs):
    raise AssertionError("check.py tried the network in a test")


class Machine(unittest.TestCase):
    """A machine whose evo-agents is a uv tool installed from git at OLD, while nightly points to NIGHTLY."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="update-evo-agents-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.status_path = self.tmp / "status.json"
        cli = write(self.tmp / "bin" / "evo-agents", FAKE_CLI.format(version=RELEASE, status=self.status_path))
        cli.chmod(0o755)
        tools = self.tmp / "tools"
        write(tools / "evo-ak" / "uv-receipt.toml",
              '[tool]\nrequirements = [{ name = "evo-ak", extras = ["worker"], '
              'git = "https://github.com/maycuatroi1/evo-agents?rev=nightly" }]\n')
        self.installed_at(OLD)
        self.worker_home = self.tmp / "worker"
        self.worker_config(version_locked=None)

        env = {"PATH": f"{self.tmp / 'bin'}{os.pathsep}/usr/bin{os.pathsep}/bin", "HOME": str(self.tmp / "home"),
               "UV_TOOL_DIR": str(tools), "EVO_WORKER_HOME": str(self.worker_home)}
        for patch in (
            mock.patch.dict(os.environ, env),
            mock.patch.object(check, "latest_versions", lambda use_cache: {
                "evo-ak": RELEASE, "plugins": {}, "source": "network"}),
            mock.patch.object(check, "nightly_state", lambda use_cache: {
                "tag": "nightly", "commit": NIGHTLY, "source": "network"}),
            mock.patch.object(check, "fetch_json", no_network),
            mock.patch.object(check, "HUB_CONFIG", self.tmp / "home" / "no-hub.json"),
            mock.patch.object(check, "REGISTRIES", ()),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def installed_at(self, commit: str) -> None:
        dist = self.tmp / "tools" / "evo-ak" / "lib" / "python3.12" / "site-packages" / f"evo_ak-{RELEASE}.dist-info"
        write(dist / "direct_url.json", json.dumps({
            "url": "https://github.com/maycuatroi1/evo-agents",
            "vcs_info": {"vcs": "git", "commit_id": commit, "requested_revision": "nightly"}}))

    def worker_config(self, **fields) -> None:
        config = {"url": "https://hub.example", "worker_id": "w1", "name": "mac", "projects": [], **fields}
        write(self.worker_home / "config.json", json.dumps(config))

    def hub_says(self, hub: dict | None, daemon_pid: int | None = 4242) -> None:
        """What `evo-agents worker status --json` prints: `hub` is GET /v1/workers/{id}, null when not signed in."""
        write(self.status_path, json.dumps({"name": "mac", "daemon_pid": daemon_pid, "hub": hub, "hub_error": None}))

    def harness(self, name: str, workflow: str) -> Path:
        root = self.tmp / name
        write(root / "harness.yaml", f"name: {name}\n")
        write(root / ".github" / "workflows" / "harness-validate.yaml", workflow)
        return root

    def text(self, report: dict) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            check.print_report(report)
        return out.getvalue()

    def main(self, *argv: str) -> str:
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["check.py", *argv]), contextlib.redirect_stdout(out):
            self.assertEqual(check.main(), 0)
        return out.getvalue()


def hub_view(**fields) -> dict:
    return {"status": "online", "agent_version": RELEASE, "agent_commit": OLD, "held_runs": 0, "drained_at": None,
            **fields}


class HarnessCI(Machine):
    def test_nightly_line_is_current(self) -> None:
        state = check.harness_state(self.harness("follows", FOLLOWS_NIGHTLY))
        self.assertEqual([(i["kind"], i["ref"], i["line"]) for i in state["installs"]], [("nightly", "nightly", 9)])
        self.assertTrue(state["nightly"])
        self.assertEqual(state["locked_at"], [], "the evo-ak==0.22.1 of a comment installs nothing")
        self.assertNotIn("behind", state)

    def test_pinned_line_is_locked_not_behind(self) -> None:
        self.hub_says(hub_view(version_locked=False, self_update={"state": "current"}))
        self.installed_at(NIGHTLY)
        root = self.harness("pinned", PINNED)
        report = check.build(args(local=False, harness=[str(root)]))
        (entry,) = report["harnesses"]
        self.assertEqual(entry["locked_at"], ["0.16.1"])
        self.assertFalse(entry["nightly"])
        self.assertEqual(report["behind"], [])
        text = self.text(report)
        self.assertIn(".github/workflows/harness-validate.yaml:10 locked at 0.16.1 (latest release 0.22.1)", text)
        self.assertNotIn("BEHIND", text)
        self.assertIn("behind: nothing", text)

    def test_other_git_ref_is_reported_as_it_is(self) -> None:
        installs = check.ci_installs({"ci.yml": "run: uv tool install "
                                      "'evo-ak[graphify] @ git+https://github.com/maycuatroi1/evo-agents.git@v0.22.1'\n"
                                      "run: pip install git+https://github.com/maycuatroi1/evo-agents@nightly#egg=evo-ak"})
        self.assertEqual([(i["kind"], i["ref"]) for i in installs], [("git", "v0.22.1"), ("nightly", "nightly")])
        self.assertEqual(check.install_text(installs[0], RELEASE), "git @v0.22.1")

    def test_reads_the_default_branch_not_the_working_tree(self) -> None:
        root = self.harness("branch", PINNED)
        git(root, "init", "-q")
        git(root, "add", ".")
        git(root, "commit", "-q", "-m", "pinned")
        git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        write(root / ".github" / "workflows" / "harness-validate.yaml", FOLLOWS_NIGHTLY)
        state = check.harness_state(root)
        self.assertEqual(state["ref"], "origin/main")
        self.assertEqual(state["locked_at"], ["0.16.1"])


class WorkerLock(Machine):
    def test_cli_at_nightly_is_current(self) -> None:
        self.installed_at(NIGHTLY)
        self.hub_says(hub_view(version_locked=False, agent_commit=NIGHTLY, self_update={"state": "current"}))
        report = check.build(args())
        self.assertIsNone(report["cli"]["action"])
        self.assertEqual(report["behind"], [])

    def test_locked_worker_holds_the_cli(self) -> None:
        self.hub_says(hub_view(version_locked=True, self_update={"state": "locked", "reason": "locked by its owner"}))
        report = check.build(args())
        cli, worker = report["cli"], report["worker"]
        self.assertEqual(cli["action"], "reinstall at nightly")
        self.assertIn("locked on the hub", cli["held"])
        self.assertFalse(cli["behind"])
        self.assertEqual((worker["version_locked"], worker["lock_source"]), (True, "hub"))
        self.assertFalse(worker["behind"])
        self.assertFalse(worker["self_updating"])
        self.assertEqual(report["behind"], [])
        text = self.text(report)
        self.assertIn("HELD, not reinstall at nightly", text)
        self.assertIn("version: locked on the hub", text)

    def test_unlocked_worker_leaves_the_cli_behind(self) -> None:
        self.hub_says(hub_view(version_locked=False, self_update={"state": "waiting", "reason": "1 run held"}))
        report = check.build(args())
        self.assertTrue(report["cli"]["behind"])
        self.assertIsNone(report["cli"]["held"])
        self.assertEqual(report["behind"], [f"CLI {RELEASE} (git bbbbbbb) -> nightly aaaaaaa"])

    def test_daemon_installing_nightly_holds_the_cli(self) -> None:
        self.hub_says(hub_view(version_locked=False, self_update={"state": "updating"}))
        report = check.build(args())
        self.assertIn("installing nightly now", report["cli"]["held"])
        self.assertFalse(report["cli"]["behind"])
        self.assertFalse(report["worker"]["behind"])

    def test_lock_from_config_json_when_the_hub_was_not_read(self) -> None:
        self.worker_config(version_locked=True)
        self.hub_says(None)
        report = check.build(args())
        self.assertEqual((report["worker"]["version_locked"], report["worker"]["lock_source"]), (True, "config.json"))
        self.assertTrue(report["cli"]["held"])
        self.assertIn("as config.json kept it", self.text(report))

    def test_unknown_lock_holds_nothing(self) -> None:
        self.hub_says(hub_view())  # a hub before schema 0048: no version_locked, no self_update
        report = check.build(args())
        self.assertIsNone(report["worker"]["version_locked"])
        self.assertTrue(report["cli"]["behind"])
        self.assertIn("lock unknown", self.text(report))


class DaemonSelfUpdate(Machine):
    def test_self_updating_daemon_is_not_restarted(self) -> None:
        update = {"state": "waiting", "reason": "1 run held", "nightly_commit": NIGHTLY,
                  "checked_at": "2026-10-19T09:00:00Z", "since": "2026-10-19T08:00:00Z"}
        self.hub_says(hub_view(version_locked=False, self_update=update))
        report = check.build(args())
        worker = report["worker"]
        self.assertTrue(worker["self_updating"])
        self.assertFalse(worker["behind"])
        self.assertEqual(worker["self_update"], update)
        self.assertNotIn("worker daemon", "; ".join(report["behind"]))
        self.assertIn("self-update: waiting; 1 run held; nightly aaaaaaa as of 2026-10-19T09:00:00Z", self.text(report))

    def test_daemon_that_has_not_heard_the_lock_is_not_self_updating(self) -> None:
        self.hub_says(hub_view(self_update={"state": "waiting", "reason": "the hub has not said"}))
        report = check.build(args())
        self.assertFalse(report["worker"]["self_updating"], "it would not restart on a new install")
        self.assertTrue(report["worker"]["behind"])

    def test_failed_update_is_reported(self) -> None:
        update = {"state": "current", "error": "uv tool install failed", "error_at": "2026-10-19T07:00:00Z"}
        self.hub_says(hub_view(version_locked=False, self_update=update))
        self.assertIn("last update failed at 2026-10-19T07:00:00Z: uv tool install failed",
                      self.text(check.build(args())))

    def test_daemon_that_cannot_update_itself_is_behind(self) -> None:
        self.hub_says(hub_view(version_locked=False, self_update={"state": "unsupported", "reason": "run by hand"}))
        report = check.build(args())
        self.assertFalse(report["worker"]["self_updating"])
        self.assertTrue(report["worker"]["behind"])
        self.assertIn(f"worker daemon {RELEASE}", report["behind"])

    def test_daemon_without_self_update_is_behind_with_the_cli(self) -> None:
        self.hub_says(hub_view(version_locked=False))
        report = check.build(args())
        self.assertTrue(report["worker"]["behind"])
        self.assertIn("not reported (a daemon without self-update", self.text(report))

    def test_locked_daemon_is_left_alone(self) -> None:
        self.hub_says(hub_view(version_locked=True, agent_version="0.20.0", self_update={"state": "locked"}))
        self.assertFalse(check.build(args())["worker"]["behind"])


class Notice(Machine):
    def setUp(self) -> None:
        super().setUp()  # no status.json: the notice never asks the hub
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.harness("pinned", PINNED))

    def test_silent_when_the_worker_is_locked(self) -> None:
        self.worker_config(version_locked=True)
        self.assertEqual(self.main("--notice"), "")

    def test_names_the_cli_but_not_the_locked_harness(self) -> None:
        self.worker_config(version_locked=False)
        line = self.main("--notice")
        self.assertTrue(line.startswith("evo-agents update: CLI 0.22.1 (git bbbbbbb) -> nightly aaaaaaa."), line)
        self.assertNotIn("pinned", line)

    def test_json_local_reads_no_harness(self) -> None:
        self.hub_says(hub_view(version_locked=True, self_update={"state": "locked"}))
        report = json.loads(self.main("--json", "--local"))
        self.assertEqual(report["harnesses"], [])
        self.assertTrue(report["worker"]["version_locked"])
        self.assertEqual(report["behind"], [])


if __name__ == "__main__":
    unittest.main()
