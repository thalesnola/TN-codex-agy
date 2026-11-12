---
name: codex-argon
description: Distribuir tarefas pelo AGY entre modelos Gemini, com o Codex no comando, para exploração, implementação por patch e revisão em contexto separado.
---

# Codex → AGY

Use as ferramentas `argon_*` disponíveis; se não estiverem expostas, use a CLI instalada do projeto. Não alegue que um MCP registrado já está disponível na sessão.

O Codex define objetivo, escopo, arquivos de responsabilidade, critérios de aceite e dependências. Envie especificações compactas; não copie o histórico inteiro. Consulte catálogo e rotas antes de escolher modelo. Apenas Gemini: nenhuma falha autoriza Claude, Opus, Sonnet ou outro provedor.

Delegue exploração volumosa, trabalho delimitado em arquivos distintos e revisão de um patch pronto. Perguntas simples podem continuar no Codex. Submeta tarefas independentes em paralelo dentro do limite configurado; dependências de decisão aguardam aceitação explícita pelo Codex.

Leia o resumo e os artefatos necessários. Confirme achados acionáveis no código. Para revisão de implementação, forneça o snapshot resultante do executor, em novo contexto. O executor não aprova sua própria alteração.

Antes de aplicar um patch, confira o diff, os arquivos sob responsabilidade e se a base ainda corresponde à origem. O AGY não altera a origem. O Codex aplica e executa testes proporcionais. Não entregue uma tentativa interrompida como sucesso nem continue escrita parcial usando outro modelo.

Mantenha acompanhamento até conclusão, falha ou necessidade real de informação. Informe modelo efetivamente usado, validação e limitações; campos de uso ausentes não são zero medido.
