# Wait for CI in the background

Part of the execute-plan skill: its section 6 says when to read this file. Section numbers here are those of
the skill's `SKILL.md`.

A step's verify, or a merge the plan asks for, may need the CI of a pull request: the verify calls
`gh pr checks` or checks that the PR is merged, or the plan says the checks must pass before the merge.
After the main session pushes such a branch or opens such a PR, it waits for the PR's required checks
itself, in the background. It never runs `sleep` in the foreground and never asks the user to say when
CI is done. On one plan, a red CI went unnoticed for almost four hours because the session stopped to
wait and only the user's message woke it. On others the person had to write "CI xanh rồi, merge đi"
(CI is green, merge): the session had asked for the merge only after CI, or had marked a step "waiting
for CI of PR #37", run a one-shot `gh pr checks` and ended its turn. Plan-step subagents keep their
rules (no push, no pull request, no rebase), so the wait belongs to the main session.

Start the watch as a background command. In Claude Code that is Bash with `run_in_background: true`,
which wakes the session when the command exits. In Codex, `exec_command` hands back a session id when the
command is still running after its `yield_time_ms`; check the watch between steps with `write_stdin` and
empty `chars`, and when no ready step is left, keep polling it with a long `yield_time_ms` rather than
ending the turn. Another runtime uses its own way to wait on a command.

```sh
end=$(( $(date +%s) + 5400 ))
gh pr checks <pr> --repo <owner/repo> --watch --required --fail-fast --interval 60 & w=$!
while kill -0 $w 2>/dev/null; do
  [ "$(date +%s)" -lt "$end" ] || { kill $w; echo "ci-wait: no result after 90 minutes"; exit 124; }
  sleep 10
done
wait $w
```

While it runs, go on with ready steps that do not depend on it, and end the turn when none is left.
Never end a turn while a step's evidence or the status line says it waits for CI unless a background
watch for that PR or run is still running. A one-shot `gh pr checks` or `gh run view` is
a look, not a wait: it wakes nobody when CI ends. A merge consent asked as section 6 says is acted on when
this watch ends.
When the command ends, read only the last lines of its output and act on its exit status:

- `0`: every required check passed. Do what was waiting: run the step's verify and record it as section
  5 says, or merge now, without asking. Suites of the verify that this CI ran green on the same commit are not run again locally: cite
  the CI run in the evidence and run only the rest of the verify.
- `1`, printing `no checks reported` or `no required checks reported` at once: CI has not registered the
  push yet, or the PR has no required check. `gh run list --repo <owner/repo> --commit <sha>` tells
  which. Start the watch again, without `--required` when the PR has checks but none is required. When
  no workflow runs on the commit there is no CI to wait for; say so in the status line instead of
  inventing a check.
- `1` otherwise: a required check failed. Read the failed log of its whole workflow run, not only its
  job: a required check is often a summary job whose log says only that another job failed. The run id
  is the number after `/actions/runs/` in the link.

  ```
  gh pr checks <pr> --repo <owner/repo> --required --json name,bucket,link -q '.[] | select(.bucket=="fail") | .link'
  gh run view <run-id> --repo <owner/repo> --log-failed > "${TMPDIR:-/tmp}/ci-<run-id>.log"; tail -n 80 "${TMPDIR:-/tmp}/ci-<run-id>.log"
  ```

  Spawn a fresh plan-step subagent on the step whose verify or merge waits on this CI, with the PR, the
  failed job, the log file and its failing lines as `context`; the step stays `pending`. Push the
  subagent's commits to the same branch, never forced, and
  start the watch again. When the log shows nothing from the repo's own commands (a lost runner, a
  cancelled run, a download that timed out), rerun the failed jobs once with
  `gh run rerun <run-id> --repo <owner/repo> --failed` instead of spawning a fix. When the same check is
  still red after two fix rounds, treat the step as failed (section 8).
- `124`: no result after 90 minutes. Ask the user, naming the PR and the checks still pending
  (`gh pr checks <pr> --repo <owner/repo> --required`), whether to wait longer or stop there.

A push with no pull request, straight to a branch the plan names, has no PR checks. Wait on the
workflow runs of the pushed commit instead: one wrapper as above for each id that
`gh run list --repo <owner/repo> --commit <sha> --json databaseId -q '.[].databaseId'` prints, with
`gh run watch <run-id> --repo <owner/repo> --exit-status --interval 60` in place of the `gh pr checks`
line. An empty list right after the push means CI has not started, not that it passed.

A `gh` that is missing or not signed in is an environmental blocker (section 8).

## Checklist

- [ ] After a push or pull request whose CI a step's verify or a merge needs: required checks watched in
      the background with a 90-minute limit, no foreground `sleep`, no request that the user report CI;
      a red check's run read with `gh run view --log-failed` and handed to a fix subagent; the user asked
      only when 90 minutes passed without a result.
