#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

CMD="${1:-up}"

case "$CMD" in
  up)
    echo "==> installing deps"
    # <install step>

    echo "==> starting dev server"
    # <the ONE command that boots this thing>
    # Print the URL. An agent that cannot find the URL cannot verify anything.
    ;;

  test)
    # <the ONE command that runs the tests>
    ;;

  e2e)
    # <how to drive this as a user would - browser automation, a CLI harness, whatever applies>
    # Without this, an agent will mark features done that do not work.
    ;;

  smoke)
    # <the 10-second check that the app is not broken>
    # This runs at the START of a session, before any new work. A repo left broken by the previous
    # session must be fixed before new code makes the mess larger.
    ;;

  down)
    # <teardown>
    ;;

  *)
    echo "usage: ./init.sh [up|test|e2e|smoke|down]" >&2
    exit 1
    ;;
esac
