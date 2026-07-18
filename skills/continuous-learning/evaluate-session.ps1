# Windows Stop-hook entry for continuous-learning.
# Mirrors evaluate-session.sh: reads the hook JSON from stdin, applies the same guards,
# then launches extract_patterns.py DETACHED (non-blocking) so session end isn't delayed.
# Always exits 0 — a learning hook must never block or fail the session.

$ErrorActionPreference = 'SilentlyContinue'

try {
    # Recursion guard: the child `claude -p` invocation runs with this env set.
    if ($env:CONTINUOUS_LEARNING_CHILD -eq '1') { exit 0 }

    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $config    = Join-Path $scriptDir 'config.json'
    $extractor = Join-Path $scriptDir 'extract_patterns.py'

    # Read the entire hook payload from stdin.
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

    $payload = $raw | ConvertFrom-Json
    $cwd        = $payload.cwd
    $transcript = $payload.transcript_path
    $sessionId  = $payload.session_id
    $stopActive = $payload.stop_hook_active

    if ([string]::IsNullOrWhiteSpace($cwd) -or
        [string]::IsNullOrWhiteSpace($transcript) -or
        [string]::IsNullOrWhiteSpace($sessionId)) { exit 0 }

    if ($stopActive -eq $true) { exit 0 }
    if (-not (Test-Path -LiteralPath $transcript -PathType Leaf)) { exit 0 }

    # Skip sessions already processed.
    $processed = Join-Path $cwd ".claude\skills\learned\.processed\$sessionId"
    if (Test-Path -LiteralPath $processed) { exit 0 }

    # Resolve a Python interpreter.
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) { $py = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
    if (-not $py -and (Test-Path "$env:USERPROFILE\miniconda3\python.exe")) {
        $py = "$env:USERPROFILE\miniconda3\python.exe"
    }
    if (-not $py) { exit 0 }

    $log    = Join-Path $env:TEMP "continuous-learning-$sessionId.log"
    $errLog = "$log.err"

    # Launch the extractor detached. Start-Process returns immediately (no -Wait),
    # and the child survives this hook process exiting.
    $env:CONTINUOUS_LEARNING_CHILD = '1'
    $argline = "`"$extractor`" --transcript `"$transcript`" --cwd `"$cwd`" --session-id `"$sessionId`" --config `"$config`""
    Start-Process -FilePath $py -ArgumentList $argline -WindowStyle Hidden `
        -RedirectStandardOutput $log -RedirectStandardError $errLog | Out-Null
}
catch {
    # Never let the hook fail the session.
}
exit 0
