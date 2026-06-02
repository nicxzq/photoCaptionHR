$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath failed with exit code $LASTEXITCODE."
    }
}

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

Invoke-Checked $venvPython @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked $venvPython @("-m", "pip", "install", "-r", "requirements.txt")
$distExe = Join-Path $PSScriptRoot "dist/photosign.exe"
$distCliExe = Join-Path $PSScriptRoot "dist/photosign-cli.exe"
Remove-Item -LiteralPath $distExe -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $distCliExe -Force -ErrorAction SilentlyContinue
Invoke-Checked $venvPython @("-m", "PyInstaller", "--clean", "photosign.spec")

$release = Join-Path $PSScriptRoot "release"
New-Item -ItemType Directory -Force -Path $release | Out-Null
Copy-Item -Force $distExe (Join-Path $release "photosign.exe")
Copy-Item -Force $distCliExe (Join-Path $release "photosign-cli.exe")
$externalModels = Join-Path $release "models"
if (Test-Path $externalModels) {
    Remove-Item -LiteralPath $externalModels -Recurse -Force
}
New-Item -ItemType Directory -Force -Path (Join-Path $release "input") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $release "output") | Out-Null
Copy-Item -Force (Join-Path $PSScriptRoot "README.md") (Join-Path $release "README.md")

Write-Host "Built release/photosign.exe"
Write-Host "Built release/photosign-cli.exe"
Write-Host "PaddleOCR models are bundled inside release/photosign.exe."
