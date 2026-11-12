# Teste completo: edição sintética com revisão antes da aplicação

Este cenário valida Codex → MCP → worker → AGY → Gemini → patch → revisão/testes pelo Codex → aplicação na origem → testes finais → aceite. Os arquivos são inteiramente sintéticos. Use somente uma cópia do exemplo e preserve as instruções mais restritivas da sua configuração. O processo AGY é local, mas a inferência Gemini ocorre em nuvem.

## Execução observada em 4 de novembro de 2026

Ambiente: Windows, Python 3.12.10, ponte 0.1.0 com descoberta do Git corrigida. Modelo efetivo: `gemini-4-argon-low`, uma tentativa.

| Etapa | Resultado observado |
| --- | --- |
| Antes da submissão | Oito testes executados; cinco falharam com o código defeituoso. Hashes da origem registrados. |
| Edição no snapshot | Job terminou em `succeeded`, ainda não aceito. Somente `calc.py` alterado; nenhum patch aplicado à origem pela ponte. |
| Conferência pelo Codex | Manifesto-base compatível com os hashes da origem; origem e testes intactos. Patch lido e limitado à expressão de retorno. |
| Revisão independente | Outra instância Codex aprovou estaticamente limites inclusivos, assinatura, docstring e erro de intervalo inválido; nenhum problema acionável. |
| Validação anterior à aplicação | Oito testes passaram no snapshot; `git apply --check` passou na origem. |
| Aplicação pelo Codex | O patch revisado foi aplicado somente à cópia sintética da origem. |
| Validação posterior | Oito testes passaram na origem; arquivo de testes conservou o hash inicial. Texto do código correspondeu ao snapshot revisado. |
| Aceite | `argon_accept` foi chamado somente depois das verificações e dos testes finais. |

A alteração foi:

```diff
-    return min(lower, max(upper, value))
+    return max(lower, min(upper, value))
```

O Gemini não executou os testes: recebeu instrução de não usar shell/MCP. O Codex executou os testes reais e conferiu os resultados, em vez de aceitar a avaliação estática apresentada pelo executor.

Git preservou CRLF na origem enquanto o snapshot usava LF. A comparação binária posterior detectou a diferença; a comparação de texto com normalização de quebras de linha confirmou a equivalência. O hash do arquivo de testes permaneceu idêntico. Essa normalização não dispensa revisar qualquer outra diferença de conteúdo.

## Arquivos do exemplo

- [`calc.py`](../examples/clamp/calc.py): versão propositalmente defeituosa; não substituir pela corrigida no exemplo-base.
- [`test_calc.py`](../examples/clamp/test_calc.py): oito testes cobrindo valores abaixo/dentro/acima, limites, negativos, float, intervalo de largura zero e intervalo invertido.
- [`task.example.json`](../examples/clamp/task.example.json): contrato de implementação; substitua caminho e chave antes de enviar.
- [`expected.patch`](../examples/clamp/expected.patch): patch de referência, que também permite reproduzir a validação offline. Uma resposta real pode produzir outro diff correto; revise-o.

Os testes do exemplo estão fora de `tests/`, pois devem falhar com a versão-base. Não adicione a pasta a uma descoberta global de testes esperando sucesso inicial.

## Preparar uma cópia isolada

Execute a partir da raiz do checkout, em PowerShell 5.1. Python, Git e dependências da ponte devem estar instalados. Todos os caminhos derivados abaixo pertencem apenas ao exemplo criado nesta execução.

```powershell
$repoRoot = (Get-Location).Path
$argonPython = Join-Path $repoRoot '.venv/Scripts/python.exe'
$gitCommand = Get-Command git -ErrorAction SilentlyContinue
$gitExe = if ($gitCommand) { $gitCommand.Source } else {
    @((Join-Path $env:ProgramFiles 'Git/cmd/git.exe'), (Join-Path $env:LOCALAPPDATA 'Programs/Git/cmd/git.exe')) |
        Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
if (-not $gitExe) { throw 'Instale Git ou configure seu caminho antes de continuar' }
$sampleRoot = Join-Path $repoRoot 'examples/clamp'
$runRoot = Join-Path ([IO.Path]::GetTempPath()) ('codex-argon-clamp-' + [Guid]::NewGuid().ToString('N'))
$sourceRoot = Join-Path $runRoot 'source'
New-Item -ItemType Directory -Path $sourceRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $sampleRoot 'calc.py') -Destination $sourceRoot
Copy-Item -LiteralPath (Join-Path $sampleRoot 'test_calc.py') -Destination $sourceRoot
$calcHash = (Get-FileHash -LiteralPath (Join-Path $sourceRoot 'calc.py') -Algorithm SHA256).Hash
$testsHash = (Get-FileHash -LiteralPath (Join-Path $sourceRoot 'test_calc.py') -Algorithm SHA256).Hash
Push-Location $sourceRoot
try { & $argonPython -B -m unittest -v } finally { Pop-Location }
# Esperado: oito testes executados, cinco falhas, código de saída não zero.
```

Não use o checkout de um projeto real como `source`. O exemplo inclui somente os dois arquivos selecionados; não acrescente configurações pessoais ou dados de caso.

## Repetição online via MCP ou CLI

Esta etapa chama Gemini de verdade e pode consumir cota. Consulte `argon_status` e `argon_models` no cliente Codex. Prossiga somente com um Gemini permitido e disponível; não use Claude/Anthropic como fallback.

```powershell
$task = Get-Content -LiteralPath (Join-Path $sampleRoot 'task.example.json') -Raw | ConvertFrom-Json
$task.source = $sourceRoot.Replace('\', '/')
$task.idempotency_key = 'clamp-' + [Guid]::NewGuid().ToString('N')
$taskPath = Join-Path $runRoot 'task.json'
$task | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $taskPath -Encoding UTF8
& $argonPython -m codex_argon status
& $argonPython -m codex_argon models --refresh
& $argonPython -m codex_argon submit $taskPath
```

Alternativamente, passe o objeto JSON já preenchido em `task` para `argon_submit`. Guarde o ID retornado e acompanhe com `argon_result` ou `python -m codex_argon result <job-id>` até estado terminal. A execução online não faz parte da suíte automatizada normal.

Não aceite nem aplique se houver falha, cancelamento ou resultado incompleto. Para sucesso, confira modelo efetivo, `status=ok`, `state=succeeded`, `accepted=false` e `changed_files` contendo somente `calc.py`. Leia `artifact=response` e `artifact=patch`. Identifique o caminho real de `snapshot` e o arquivo de patch retornado pela ponte; não reutilize IDs ou caminhos de outra máquina.

## Revisar e validar antes de aplicar

O Codex deve conferir a alteração de retorno, os limites inclusivos e o `ValueError` preservado. Compare o manifesto-base com a origem atual; neste exemplo, os dois hashes originais também devem permanecer inalterados até a aplicação. Confirme que o teste no snapshot corresponde ao original. Faça revisão independente em contexto separado para reproduzir o fluxo observado.

Preencha as duas variáveis abaixo somente com os caminhos dos artefatos do job atual, depois de inspecioná-los:

```powershell
$snapshotRoot = 'CAMINHO_ABSOLUTO_DO_SNAPSHOT_DO_JOB'
$patchPath = 'CAMINHO_ABSOLUTO_DO_PATCH_DO_JOB'
if ((Get-FileHash -LiteralPath (Join-Path $sourceRoot 'calc.py') -Algorithm SHA256).Hash -ne $calcHash) { throw 'Origem mudou antes da aplicação' }
if ((Get-FileHash -LiteralPath (Join-Path $sourceRoot 'test_calc.py') -Algorithm SHA256).Hash -ne $testsHash) { throw 'Teste da origem mudou' }
if ((Get-FileHash -LiteralPath (Join-Path $snapshotRoot 'test_calc.py') -Algorithm SHA256).Hash -ne $testsHash) { throw 'Executor alterou os testes' }
Push-Location $snapshotRoot
try {
    & $argonPython -B -m unittest -v
    if ($LASTEXITCODE -ne 0) { throw 'Testes do snapshot falharam' }
} finally { Pop-Location }
& $gitExe -C $sourceRoot apply --check $patchPath
if ($LASTEXITCODE -ne 0) { throw 'Patch não corresponde à origem' }
```

Registre os resultados e a decisão do Codex. O sucesso do job ou uma revisão gerada pelo modelo não substitui esta conferência. Os comandos seguintes são uma etapa manual separada, a executar somente após a revisão e todas as validações anteriores:

```powershell
# Reconfira a base imediatamente antes de escrever.
if ((Get-FileHash -LiteralPath (Join-Path $sourceRoot 'calc.py') -Algorithm SHA256).Hash -ne $calcHash) { throw 'Origem mudou após a revisão' }
if ((Get-FileHash -LiteralPath (Join-Path $sourceRoot 'test_calc.py') -Algorithm SHA256).Hash -ne $testsHash) { throw 'Testes mudaram após a revisão' }
& $gitExe -C $sourceRoot apply --check $patchPath
if ($LASTEXITCODE -ne 0) { throw 'Patch inválido para esta origem' }
& $gitExe -C $sourceRoot apply $patchPath
if ($LASTEXITCODE -ne 0) { throw 'Falha ao aplicar o patch' }
if ((Get-FileHash -LiteralPath (Join-Path $sourceRoot 'test_calc.py') -Algorithm SHA256).Hash -ne $testsHash) { throw 'Teste mudou após a aplicação' }
Push-Location $sourceRoot
try {
    & $argonPython -B -m unittest -v
    if ($LASTEXITCODE -ne 0) { throw 'Testes finais falharam; não aceitar o job' }
} finally { Pop-Location }
```

Confira também que o texto aplicado corresponde ao snapshot revisado, considerando somente a normalização explícita LF/CRLF. Após a aprovação final, use `argon_accept` ou `python -m codex_argon accept <job-id>`. Aceitar o job não aplica o patch: são operações distintas sob responsabilidade do Codex.

## Reprodução offline do exemplo

Prepare uma nova cópia isolada como acima. Depois de observar as cinco falhas iniciais, use `expected.patch` como `$patchPath`, leia o diff e valide com `git apply --check`. Aplique à cópia e execute os oito testes novamente: devem passar sem alterar `test_calc.py`. Isso valida código, testes e patch de referência, mas não comprova autenticação, catálogo ou inferência real.

## Limites e evidências

O registro descreve uma execução observada, não desempenho típico ou uma garantia técnica de aprovação humana/modelo antes de toda aplicação futura. O worker não edita a origem; a decisão de aplicar continua com o Codex. Não foi adicionada rotina de autoaplicação. Os controles são de aplicação e não equivalem a uma sandbox de sistema operacional.

Registre hashes e resultados localmente ao repetir o cenário. Logs brutos, banco de jobs, perfis AGY, credenciais e caminhos pessoais não devem ser enviados ao repositório. Este guia publica somente o resultado resumido e os arquivos sintéticos portáveis.
