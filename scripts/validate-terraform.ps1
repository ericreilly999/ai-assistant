$ErrorActionPreference = "Stop"

function Resolve-TerraformCommand {
    $installRoots = @(
        (Join-Path $env:LocalAppData "Microsoft\WinGet\Packages"),
        "C:\Program Files\Terraform"
    )

    foreach ($root in $installRoots) {
        if (-not (Test-Path $root)) {
            continue
        }

        $terraform = Get-ChildItem $root -Recurse -Filter terraform.exe -ErrorAction SilentlyContinue |
            Select-Object -First 1

        if ($terraform) {
            return $terraform.FullName
        }
    }

    $command = Get-Command terraform -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "Terraform is not available on PATH. Install Terraform to validate the infrastructure scaffold."
}

$terraform = Resolve-TerraformCommand
& $terraform fmt -check -recursive terraform
foreach ($environment in @("dev", "staging", "prod")) {
    & $terraform -chdir="terraform/environments/$environment" init -backend=false
    & $terraform -chdir="terraform/environments/$environment" validate
}