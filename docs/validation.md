# Validação — 04/11/2026

Implementação local 0.1.0, Windows, Python 3.12.10, AGY backend 1.5.0.

## Verificações concluídas

- Suíte automatizada: 16 testes passaram, incluindo allowlist, parser, idempotência, dependências com aceite, colisões entre origens aninhadas, cancelamento, descendentes, snapshot, escopo de edição, revisão e paginação.
- Revisão independente: achados principais corrigidos; nenhum achado alto pendente no MVP.
- MCP STDIO real: negociação, listagem das sete ferramentas e `argon_status` sem erro.
- Catálogo real: seis Gemini disponíveis, consultados pelo perfil separado da ponte.
- Implementação real: `gemini-3.8-flash-medium` corrigiu uma função sintética no snapshot. Patch conferido; origem permaneceu intacta. Três verificações de soma passaram no snapshot.
- Revisão real: `gemini-4-argon-medium`, em outro job e contexto, recebeu o snapshot corrigido e confirmou a alteração. Nenhum arquivo modificado pelo revisor.
- Skill validada e instalada; MCP registrado no Codex. Descoberta na sessão aberta depende de recarregar o cliente.

## Medições das duas sondas

| Job | Tempo informado pela ponte | Tokens entrada | Tokens saída |
|---|---:|---:|---:|
| Implementação / Flash Medium | 26,344 s | 31.478 | 862 |
| Revisão / Argon Medium | 31,156 s | 12.063 | 1.001 |

Uso reportado pelo AGY, sem estimativa de preço. Uma amostra por tarefa não estabelece desempenho típico ou economia de créditos. As duas sondas ocorreram antes dos últimos ajustes de limpeza de processos, cobertos pela suíte final.

## Limites conhecidos

- Pesquisa web: capacidade ainda não validada; não prometer fontes coletadas pela ponte sem sonda específica.
- Retenção automática de artefatos não implementada; jobs e perfis permanecem no estado local. Não incluir o diretório de estado em commits.
- Resultados atuais são texto AGY validado em envelope JSON. O schema de revisão é referência de contrato, não imposição automática de revisão estruturada.
- Integração e aplicação do patch pertencem ao Codex; a ponte não aplica alterações na origem.
- A configuração do AGY restringe operações de arquivo, shell e MCP. Não equivale a uma sandbox de sistema operacional. Existe pequena janela entre criação do processo e associação ao Job Object no Windows.
- macOS não validado; esta entrega foi testada no Windows.
- O SDK MCP emite um aviso de forward reference com as versões Pydantic fixadas; negociação e ferramentas funcionaram nos testes. O aviso aparece em stderr, sem corromper o protocolo STDIO.

Nenhum Claude foi acionado. Não há auditor, detector de identificadores ou trava de sigilo no código.

## Teste completo posterior: clamp, revisão e aplicação

Em 04/11/2026, uma nova sonda com `gemini-4-argon-low` completou a edição de código via MCP, worker e AGY. A origem tinha oito testes e cinco falhas; o Gemini alterou somente `calc.py` no snapshot. O Codex verificou os hashes da origem e do arquivo de testes, revisou o diff, obteve revisão estática independente e executou os oito testes no snapshot antes da aplicação. Depois aplicou o patch, repetiu os testes na origem (oito aprovados) e registrou o aceite do job.

O retorno do AGY informou 30,281 s, 12.819 tokens de entrada, 1.185 de saída e 11.836 de leitura de cache. São contadores reportados pelo provedor; categorias podem se sobrepor e não devem ser somadas para inferir custo. Não houve chamada a outra família de modelos. A suíte local então vigente passou em 17 testes, incluindo a descoberta do Git no Windows sem PATH.

O [registro e roteiro reproduzível](end-to-end-clamp.md) e os [arquivos sintéticos](../examples/clamp) preservam o cenário sem publicar logs, credenciais, caminhos pessoais ou banco de jobs. O sucesso observado comprova esta execução; não implementa aplicação automática nem garante disponibilidade futura.
