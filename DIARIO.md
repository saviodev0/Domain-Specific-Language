# Diário de desenvolvimento

## 2026-10-14

- Conferimos a E2 e identificamos a ausência da especificação formal, do CLI de tokens, dos exemplos válidos e inválidos, do script de geração e das regras de ignore para os artefatos ANTLR.
- Ajustamos a gramática para reconhecer números reais malformados como erro léxico e movemos a saída gerada para `gerado/`, fora do Git.
- Criamos `src/lexico.py`, três exemplos válidos, três inválidos, `docs/especificacao.md` e testes para executar os exemplos pelo CLI.
- Separamos dependências de runtime e geração, fixamos o ANTLR em 4.13.2, documentamos a fase E2 e configuramos o Docker para regenerar o lexer.
- Os testes dos seis exemplos passaram; o histórico de commits permanece sem alterações automáticas.

## 2026-10-21

- Inspecionamos a especificação E2, o lexer ANTLR e sua interface de tokens, o parser manual, o interpretador, todos os exemplos e a suíte existente.
- Identificamos risco de loop infinito ao encontrar EOF antes de `}` nos blocos, além de aceitação de instruções parciais em `parse_statement` e expressões sem comparação em condições.
- A primeira validação também encontrou uma inconsistência de integração da E2: `gerar.sh` criava o módulo em `gerado/tankscript/`, mas o lexer o importa de `gerado/`; ajustamos a opção de saída exata do ANTLR para alinhar os caminhos sem alterar a gramática léxica.
- Completamos o parser recursivo preservando o formato de AST existente; agora erros sintáticos incluem linha/coluna e blocos/entradas incompletos são rejeitados.
- Registramos a gramática EBNF, a estrutura da árvore e exemplos de fronteira na especificação; atualizamos as instruções e adicionamos testes focados no parser.
- Instalamos as dependências de teste e geração já declaradas no projeto, geramos o lexer ANTLR e validamos a suíte completa: `python -m pytest -q` — 64 testes passaram.