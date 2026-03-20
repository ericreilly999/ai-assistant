Continue = \"Stop\"

function Resolve-PythonCommand {
    $installRoots = @(
        (Join-Path $env:LocalAppData "Programs\Python"),
        "C:\Python312",
        "C:\Python313"
    )

    foreach ($root in $installRoots) {
        if (-not (Test-Path $root)) {
            continue
        }

        $python = Get-ChildItem $root -Recurse -Filter python.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch "venv\\scripts" -and $_.FullName -notmatch "WindowsApps" } |
            Select-Object -First 1

        if ($python) {
            return $python.FullName
        }
    }

    foreach ($candidate in @("python", "python3", "py")) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notmatch "WindowsApps") {
            return $command.Source
        }
    }

    throw "Python is not available on PATH. Install Python 3.12+ to run backend tests."
}

 = Resolve-PythonCommand
 = (Join-Path (Get-Location) \"backend\\src\")
&  -m unittest discover -s backend/tests -t backend