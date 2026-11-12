# Arquitetura

Usuário → Codex → MCP local/CLI → fila SQLite → worker → AGY/Gemini → artefatos → Codex.

O serviço registra tarefas e devolve IDs. O worker executa fora da chamada MCP. Cada tarefa tem snapshot próprio; escrita retorna patch. As rotas aceitam somente IDs Gemini da lista explícita. A decisão final, a integração e os testes pertencem ao Codex.

Revisão usa nova chamada e o resultado produzido pelo executor. Separação de contexto entre jobs Gemini não oferece diversidade de família; o Codex faz a conferência final.

O perfil separado e as permissões do AGY controlam o comportamento da aplicação; não constituem uma sandbox de sistema operacional. Não há auditor de conteúdo nem bloqueio de pastas por classificação de sigilo.

A integração usa MCP STDIO conforme a [documentação oficial](https://learn.chatgpt.com/docs/extend/mcp). Registrar o servidor não garante descoberta imediata na sessão aberta.
