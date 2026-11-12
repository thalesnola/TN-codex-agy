[CmdletBinding()]
param([switch]$RegisterMcp, [string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvRoot = Join-Path $repoRoot '.venv'
$venvPython = Join-Path $venvRoot 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $Python -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente Python.' }
}
& $venvPython -m pip install -r (Join-Path $repoRoot 'requirements.lock')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias fixadas.' }
& $venvPython -m pip install --no-deps -e $repoRoot
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar codex-argon.' }
if ($RegisterMcp) {
    & codex mcp add codex-argon -- $venvPython -m codex_argon mcp
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao registrar MCP.' }
}
Write-Output "Instalado: $venvPython -m codex_argon"
