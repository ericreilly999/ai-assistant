$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Wait-ForUrl {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$Attempts = 20
    )

    for ($index = 0; $index -lt $Attempts; $index++) {
        try {
            Invoke-RestMethod -Uri $Url -Method Get | Out-Null
            return
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    throw "Timed out waiting for $Url"
}

$serverScript = Join-Path $PSScriptRoot "run-local-server.ps1"
$port = if ($env:LOCAL_SERVER_PORT) { $env:LOCAL_SERVER_PORT } else { "8787" }
$serverProcess = Start-Process -FilePath "powershell.exe" -ArgumentList @("-ExecutionPolicy", "Bypass", "-File", $serverScript) -WorkingDirectory $repoRoot -PassThru

try {
    Wait-ForUrl -Url "http://localhost:$port/health"

    Start-Process "http://localhost:$port/oauth/google/start" | Out-Null
    Start-Sleep -Seconds 1
    Start-Process "http://localhost:$port/oauth/microsoft/start" | Out-Null

    Write-Host "Complete the Google and Microsoft sign-in flows in your browser."
    Write-Host "When both callback pages say Connected, press Enter here to stop the local auth server."
    Read-Host | Out-Null
} finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force
    }
}
