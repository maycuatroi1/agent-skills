$ErrorActionPreference = "SilentlyContinue"

try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }

    $payload = $raw | ConvertFrom-Json
    $transcript = $payload.transcript_path
    $cwd = $payload.cwd
    $sessionId = $payload.session_id

    if (-not $transcript -or -not (Test-Path $transcript)) { exit 0 }
    if (-not $cwd -or -not $sessionId) { exit 0 }

    $script = Join-Path $PSScriptRoot "harness.py"
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) { $python = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
    if (-not $python) { exit 0 }

    & $python $script digest --transcript "$transcript" --cwd "$cwd" --session-id "$sessionId" | Out-Null
}
catch {
}

exit 0
