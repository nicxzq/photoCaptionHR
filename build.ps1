$ErrorActionPreference = "Stop"

$venvPython = Join-Path $PSScriptRoot ".venv/Scripts/python.exe"
if (-not (Test-Path $venvPython)) {
    $created = $false
    foreach ($version in @("3.11", "3.10", "3.9")) {
        py "-$version" -m venv (Join-Path $PSScriptRoot ".venv")
        if ($LASTEXITCODE -eq 0) {
            $created = $true
            break
        }
    }
    if (-not $created) {
        throw "Python 3.9, 3.10, or 3.11 is required to build PhotoSign."
    }
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt
& $venvPython -m PyInstaller --clean photosign.spec

$release = Join-Path $PSScriptRoot "release"
New-Item -ItemType Directory -Force -Path $release | Out-Null
Copy-Item -Force (Join-Path $PSScriptRoot "dist/photosign.exe") (Join-Path $release "photosign.exe")
New-Item -ItemType Directory -Force -Path (Join-Path $release "models") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $release "input") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $release "output") | Out-Null
Copy-Item -Force (Join-Path $PSScriptRoot "README.md") (Join-Path $release "README.md")

Write-Host "Built release/photosign.exe"
Write-Host "Model cache is external: use --model-dir C:\PhotoSign\models or PHOTOSIGN_MODEL_DIR."
