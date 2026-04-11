$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Resolve-PythonCommand {
    $installRoots = @(
        (Join-Path $env:LocalAppData "Programs\Python"),
        "C:\Python312",
        "C:\Python313",
        "C:\Python311"
    )

    foreach ($root in $installRoots) {
        if (-not (Test-Path $root)) { continue }
        $python = Get-ChildItem $root -Recurse -Filter python.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch "venv\\scripts" -and $_.FullName -notmatch "WindowsApps" } |
            Select-Object -First 1
        if ($python) { return $python.FullName }
    }

    foreach ($candidate in @("python", "python3", "py")) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notmatch "WindowsApps") {
            return $command.Source
        }
    }

    throw "Python is not available on PATH. Install Python 3.11+ to run the local server."
}

$python = Resolve-PythonCommand
$serverScript = Join-Path $repoRoot "backend\local_server.py"

Write-Host "Using Python: $python"
Write-Host "Starting AI Assistant local dev server..."

Set-Location $repoRoot
& $python $serverScript
