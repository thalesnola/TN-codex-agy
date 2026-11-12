# codex-argon

O Codex principal comanda, integra e valida. O AGY executa tarefas delimitadas usando apenas modelos Gemini explicitamente autorizados. Nunca acione Claude Code, modelos Claude, Opus, Sonnet ou APIs Anthropic, inclusive em fallback ou override.

Não implementar auditoria de identificadores, listas de pastas de caso ou guarda de sigilo. Controles de caminho e patch servem à integridade dos arquivos.

Preserve a origem: o executor trabalha em snapshot e devolve patch. Não aplique patches automaticamente. Revisão em nova chamada não equivale à aprovação final pelo Codex.

Execute a suíte com `python -m unittest discover -s tests -v`. Sondas reais são separadas e devem selecionar modelo Gemini explicitamente. Não registre credenciais ou arquivos de configuração pessoais no repo.
