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

## 2026-10-28

- Revisamos a E3 com base nas aulas 10 (árvore sintática), 11 (autômatos de pilha) e 12 (análise descendente).
- Escrevemos a gramática sintática em ANTLR (`tankscript/TankScriptParser.g4`), com regras de parser em minúscula, `EOF` na regra inicial e blocos recursivos; o `gerar.sh` agora gera lexer e parser.
- Fatoramos a regra `primario` na especificação: `acesso_propriedade` e `IDENTIFIER` começavam com o mesmo token (conflito de First). Corrigimos nomes de tokens misturados na EBNF.
- Documentamos terminais e não terminais, ausência de ambiguidade e de recursão à esquerda, e a tabela de First e Follow das regras de escolha.
- Criamos `src/sintatico.py` para exibir a árvore sintática e testes que conferem que o parser ANTLR e o parser manual aceitam e rejeitam os mesmos programas.
- Removemos o `antlr-4.13.2-complete.jar` do repositório: o `antlr4-tools` baixa a versão fixada em `gerar.sh`, e `*.jar` passou a ser ignorado.

## 2026-10-28 (E4)

- Implementamos a análise semântica em `tankscript/semantico.py` como *visitor* da árvore ANTLR, com tabela de símbolos de unidades, armas, equipes e batalhas.
- As regras verificam nomes (declarações repetidas, unidades, armas e equipes não declaradas, `dive`/`surface` só em submarino) e tipos (propriedades permitidas, valores inteiros, comparações entre tipos compatíveis); todos os erros são relatados com linha e coluna.
- A análise encontrou um erro real em `examples/quadrado.tank`: a batalha citava a equipe `Red`, que não existia. Adicionamos a equipe e um submarino.
- Corrigimos o interpretador: `unidade.radar` em condições sempre valia 0, porque o atributo interno se chama `radar_range`.
- O `main.py` agora executa as análises léxica, sintática e semântica antes de iniciar o jogo. Criamos `src/semantico.py`, três exemplos em `examples/invalidos_semanticos/` e `tests/test_semantico.py`.
