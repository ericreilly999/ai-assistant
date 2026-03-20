$ErrorActionPreference = "Stop"

$sourcePath = Join-Path (Get-Location) "backend\src"
$distPath = Join-Path (Get-Location) "dist"
$archivePath = Join-Path $distPath "orchestrator.zip"

New-Item -ItemType Directory -Force -Path $distPath | Out-Null
if (Test-Path $archivePath) {
    Remove-Item $archivePath -Force
}

Compress-Archive -Path (Join-Path $sourcePath "*") -DestinationPath $archivePath -Force
Write-Host "Packaged Lambda artifact at $archivePath"