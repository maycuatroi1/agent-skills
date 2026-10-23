import subprocess
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import curate
import extract_patterns

EXPECTED = {
    "CONTINUOUS_LEARNING_CHILD": "1",
    "EVO_HUB_LOCAL_SYNC": "0",
    "EVO_HUB_TRANSCRIPTS": "0",
}


def fake_run(stdout):
    return mock.Mock(return_value=subprocess.CompletedProcess(["claude"], 0, stdout=stdout, stderr=""))


def assert_child_env(run):
    assert run.call_count == 1
    args, kwargs = run.call_args
    assert args[0][:2] == ["claude", "-p"]
    env = kwargs["env"]
    for key, value in EXPECTED.items():
        assert env.get(key) == value, key


def test_child_env_sets_all_switches(monkeypatch):
    monkeypatch.setenv("EVO_HUB_TRANSCRIPTS", "1")
    monkeypatch.setenv("KEEP_ME", "yes")
    env = extract_patterns.child_env()
    for key, value in EXPECTED.items():
        assert env[key] == value
    assert env["KEEP_ME"] == "yes"


def test_call_claude_passes_child_env():
    run = fake_run('{"skills": [], "cli_suggestions": []}')
    with mock.patch.object(subprocess, "run", run):
        extract_patterns.call_claude("prompt", {})
    assert_child_env(run)


def test_consolidate_pass_passes_child_env(tmp_path):
    usage = {"skills": {
        "alpha": {"state": "active", "description": "a"},
        "beta": {"state": "active", "description": "b"},
    }}
    report = {"consolidated": []}
    run = fake_run('{"merges": []}')
    with mock.patch.object(subprocess, "run", run):
        curate.consolidate_pass(tmp_path, {}, usage, report, dry_run=True)
    assert "consolidate_error" not in report
    assert_child_env(run)
