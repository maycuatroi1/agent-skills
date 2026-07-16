param([string]$Command = "up")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

switch ($Command) {
    "up" {
        Write-Host "==> installing deps"
        # <install step>

        Write-Host "==> starting dev server"
        # <the ONE command that boots this thing>
        # Print the URL. An agent that cannot find the URL cannot verify anything.
    }

    "test" {
        # <the ONE command that runs the tests>
    }

    "e2e" {
        # <how to drive this as a user would - browser automation, a CLI harness, whatever applies>
        # Without this, an agent will mark features done that do not work.
    }

    "smoke" {
        # <the 10-second check that the app is not broken>
        # This runs at the START of a session, before any new work.
    }

    "down" {
        # <teardown>
    }

    default {
        Write-Error "usage: .\init.ps1 [up|test|e2e|smoke|down]"
        exit 1
    }
}
