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

## 2026-10-29 (interface web)

- Criamos uma interface web com Phaser 3 no estilo dos jogos de programação: o jogador escreve TankScript num editor, executa e acompanha as unidades no mapa. O Python continua sendo o motor; o navegador só desenha.
- `tankscript/partida.py` reaproveita as análises da E4 (com regras extras: limites do mapa e, no turno, só comandos para a própria equipe) e registra um evento com a linha do código e o estado do jogo a cada instrução executada. O editor destaca a linha em execução e marca os erros na posição informada pelas análises.
- `src/servidor.py` usa só a biblioteca padrão (`http.server`): serve a pasta `web/` e as rotas `/api/partidas` e `/api/partidas/<id>/turnos`.
- O `GridRenderer` passou a expor `visible_cells` e `is_shown`, usados pelo terminal e pela web; com isso, unidades reveladas por sonar fora do radar também aparecem no mapa ASCII.
- Adicionamos `tests/test_partida.py`, com testes da partida e do servidor HTTP.
- Os tipos passaram a ter atributos fixos, definidos em `tankscript/catalogo.py`: declarar uma unidade só cria uma instância e escolhe as armas. Entraram o tipo `aircraft` e a arma `missile`. A sintaxe ainda reconhece propriedades, mas a análise semântica as rejeita informando o valor do tipo; cada tipo só monta a sua arma, até 2 por unidade.
- No interpretador, cada unidade anda no máximo a sua velocidade por turno, aeronaves passam por ilhas e não se abrigam em ruínas, torpedos não atingem aeronaves e só torpedos atingem submarinos submersos. A IA se aproxima até o alcance da sua arma.
- A interface web virou uma arena: o jogador começa com o editor vazio e monta o exército com 12 pontos, o jogo gera a frota inimiga em TankScript com o mesmo orçamento, e um manual explica tipos, comandos e regras.
- O editor ganhou autocompletar por contexto (`web/completar.js`): no cenário sugere tipos e armas permitidas; no turno sugere comandos, unidades do jogador, armas da unidade, alvos inimigos, coordenadas e atributos depois do `.`.
- A IA inimiga foi refeita (`tankscript/ai.py`). Antes ela via todas as unidades do jogador; agora só vê o que o radar alcança. Para caçar na névoa, adaptamos o mapa de calor por simulação de Monte Carlo do projeto [battleships_ai](https://github.com/mitchelljy/battleships_ai), de DataSnaek (hoje mitchelljy no GitHub; licença MIT): a IA sorteia onde cada unidade do jogador pode estar desde a última vez que foi vista e vai para a região mais provável, usando sonar. Com o alvo à vista, concentra o fogo, escolhe armas que funcionam contra o alvo, recua quando tem alcance maior e mergulha os submarinos. Em 300 partidas contra a IA antiga (que via o mapa inteiro), a nova venceu cerca de 80%, perdeu menos de 2% e empatou o resto, por falta de munição ou por combinações de unidades que não conseguem se ferir. Os testes estão em `tests/test_ia.py`.
- Para deixar a partida mais difícil, o orçamento subiu para 20 pontos e a visão caiu para 2 casas ao redor de cada unidade. O sonar alcança 3 casas (tanque) ou 4 (submarino e aeronave), recarrega por 2 turnos e revela ao inimigo a posição de quem o usou; ele também deixou de marcar as unidades da própria equipe. Só é possível disparar em alvos que a equipe esteja vendo. Na IA, a caça passou a escolher o destino que deixa mais probabilidade dentro do raio de visão, e, sem nenhuma pista, ela supõe que o inimigo começou do outro lado do mapa.
