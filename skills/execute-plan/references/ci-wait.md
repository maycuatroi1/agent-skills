# Wait for a release tag's CI or a deploy in the background

Part of the execute-plan skill: its section 6 says when to read this file. Section numbers here are those of
the skill's `SKILL.md`.

A pull request's CI is never waited for: the plan's last step runs the tests the diff needs and merges at
once (section 6, The last step). What a step may still wait on is a GitHub Actions run: the CI of a release
tag (`v*`), which runs the full suite, or the workflow that deploys a merge. The main session waits for it
itself, in the background. It never runs `sleep` in the foreground and never asks the user to say when the
run is done. On one plan, a red CI went unnoticed for almost four hours because the session stopped to
wait and only the user's message woke it. Plan-step subagents keep their rules (no push, no tag, no
rebase), so the wait belongs to the main session.

Take the run's id a few seconds after the push of the tag or the merge (an empty list means it has not
started yet, not that it passed):

```sh
gh run list --repo <owner/repo> --branch <tag or branch> --workflow <file> --limit 1 --json databaseId -q '.[].databaseId'
```

Start the watch as a background command. In Claude Code that is Bash with `run_in_background: true`,
which wakes the session when the command exits. In Codex, `exec_command` hands back a session id when the
command is still running after its `yield_time_ms`; check the watch between steps with `write_stdin` and
empty `chars`, and when no ready step is left, keep polling it with a long `yield_time_ms` rather than
ending the turn. Another runtime uses its own way to wait on a command.

```sh
end=$(( $(date +%s) + 5400 ))
gh run watch <run-id> --repo <owner/repo> --exit-status --interval 60 & w=$!
while kill -0 $w 2>/dev/null; do
  [ "$(date +%s)" -lt "$end" ] || { kill $w; echo "ci-wait: no result after 90 minutes"; exit 124; }
  sleep 10
done
wait $w
```

While it runs, go on with ready steps that do not depend on it, and end the turn when none is left.
Never end a turn while a step's evidence or the status line says it waits on the run unless a background
watch for that run is still running. A one-shot `gh run view` is a look, not a wait: it wakes nobody when
the run ends. When the command ends, read only the last lines of its output and act on its exit status:

- `0`: the run passed. Record the step as section 5 says.
- `1`: a job failed. Read the failed log of the whole run:

  ```
  gh run view <run-id> --repo <owner/repo> --log-failed > "${TMPDIR:-/tmp}/ci-<run-id>.log"; tail -n 80 "${TMPDIR:-/tmp}/ci-<run-id>.log"
  ```

  A red release tag is fixed forward, never retagged: spawn a fresh plan-step subagent with the failed job,
  the log file and its failing lines as `context`, merge its fix as the last step merges, and release the
  next patch, whose tag CI is watched the same way. A red deploy is fixed the same way, with a new merge.
  When the log shows nothing from the repo's own commands (a lost runner, a cancelled run, a download that
  timed out), rerun the failed jobs once with `gh run rerun <run-id> --repo <owner/repo> --failed` instead
  of spawning a fix. When the same job is still red after two fix rounds, treat the step as failed
  (section 8).
- `124`: no result after 90 minutes. Ask the user, naming the run and the jobs still running
  (`gh run view <run-id> --repo <owner/repo>`), whether to wait longer or stop there.

A `gh` that is missing or not signed in is an environmental blocker (section 8).

## Checklist

- [ ] No wait on a pull request's CI. A release tag's CI or a deploy run a step waits on watched in the
      background with a 90-minute limit, no foreground `sleep`, no request that the user report it; a red
      run's log read with `gh run view --log-failed` and fixed forward with the next patch; the user asked
      only when 90 minutes passed without a result.
