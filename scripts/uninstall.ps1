[CmdletBinding()]
param([switch]$RemoveMcp)
$ErrorActionPreference = 'Stop'
if ($RemoveMcp) {
    & codex mcp remove codex-argon
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao remover registro MCP.' }
}
Write-Output 'Estado, tarefas e ambiente Python foram preservados.'
