# Diário de desenvolvimento

## 2026-10-14

- Conferimos a E2 e identificamos a ausência da especificação formal, do CLI de tokens, dos exemplos válidos e inválidos, do script de geração e das regras de ignore para os artefatos ANTLR.
- Ajustamos a gramática para reconhecer números reais malformados como erro léxico e movemos a saída gerada para `gerado/`, fora do Git.
- Criamos `src/lexico.py`, três exemplos válidos, três inválidos, `docs/especificacao.md` e testes para executar os exemplos pelo CLI.
- Separamos dependências de runtime e geração, fixamos o ANTLR em 4.13.2, documentamos a fase E2 e configuramos o Docker para regenerar o lexer.
- Os testes dos seis exemplos passaram; o histórico de commits permanece sem alterações automáticas.