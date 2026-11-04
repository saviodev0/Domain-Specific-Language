# Especificação da TankScript

## 1. Finalidade

TankScript é uma linguagem específica para descrever cenários de batalhas táticas entre tanques, submarinos e aeronaves. Um programa declara unidades, armas, equipas e ordens que o TankIO interpreta. Cada tipo de unidade e de arma tem atributos fixos: declarar uma unidade cria uma instância do tipo, e o programa escolhe só o nome e as armas.

## 2. Programa completo de exemplo

```tankscript
# Declara um tanque com dois canhões. Os atributos vêm do tipo tank.
tank Tiger1 {
    gun Cannon
    gun Reserve
}
# Declara um submarino com um torpedo.
submarine Shark1 {
    torpedo T1
}
# Declara uma aeronave com um míssil.
aircraft Hawk {
    missile Sidewinder
}
# Coloca o tanque e a aeronave na equipa Azul.
team Blue {
    Tiger1
    Hawk
}
# Coloca o submarino na equipa Vermelha.
team Red {
    Shark1
}
# Define a batalha entre as duas equipas.
battle War {
    Blue vs Red
}
# Define as posições iniciais.
move Tiger1 20 20
move Hawk 20 60
move Shark1 170 80
# Define a profundidade inicial do submarino.
dive Shark1 40
# Executa sonar quando a condição for verdadeira.
if Tiger1.hp > 50 {
    sonar Tiger1
}
```

## 3. Tipos de dado

- **Inteiro:** sequência de dígitos, como `100`.
- **Real:** dígitos, ponto decimal e ao menos um dígito em cada lado, como `70.5`.
- **Texto:** conteúdo entre aspas simples ou duplas, sem quebra de linha. A barra invertida pode escapar um caractere; o valor é preservado sem decodificação de escapes.
- **Identificador:** começa com letra ASCII ou sublinhado e pode continuar com letras, dígitos ou sublinhados, como `Tiger1`.

## 4. Comandos

Declarações: `tank`, `submarine`, `aircraft`, `gun`, `torpedo`, `missile`, `team` e `battle`. Uma arma é declarada só com o tipo e o nome, como `gun Cannon`.

Instruções: `move unidade x y`, `attack atacante alvo`, `fire atacante arma alvo`, `dive unidade profundidade`, `surface unidade`, `sonar unidade`, `if condição { ... }` e `repeat quantidade { ... }`.

Os atributos de unidades e armas são fixos por tipo (seção 9.2). A sintaxe ainda reconhece uma propriedade escrita como identificador seguido de número, por exemplo `hp 100`, mas a análise semântica a rejeita e informa o valor fixo do tipo.

## 5. Operadores e precedência

- `.` seleciona uma propriedade de uma unidade, como `Tiger1.hp`, e é resolvido antes da comparação.
- `<`, `>` e `==` comparam dois valores primários dentro de uma condição. As comparações têm a mesma precedência e a gramática atual permite uma comparação por condição.
- `+` e `-` são reconhecidos pelo lexer, mas ainda não são operadores de expressão aceitos pelo parser.

Não há operadores `*` ou `/` nem expressões aritméticas nesta versão.

## 6. Comentários

O caractere `#` inicia um comentário que vai até o fim da linha. Comentários e espaços em branco são descartados pelo lexer.

## 7. O que a linguagem deliberadamente não faz

1. Não declara variáveis nem permite atribuições.
2. Não calcula expressões aritméticas; valores numéricos são literais.
3. Não possui laços `while`/`for`, funções definidas pelo usuário ou chamadas de função.

## 8. Gramática sintática (E3)

A gramática sintática está em `tankscript/TankScriptParser.g4` e usa os tokens de `tankscript/TankScriptLexer.g4`. O `gerar.sh` gera o lexer e o parser ANTLR em `gerado/`. O parser manual em Python (`tankscript/parser.py`) reconhece exatamente a mesma linguagem e monta a AST usada pelo interpretador; os testes conferem que os dois aceitam e rejeitam os mesmos programas.

### 8.1 Terminais e não terminais

Seguindo a convenção do ANTLR, os **terminais** são os tokens do lexer, escritos em MAIÚSCULA (`TANK`, `IDENTIFIER`, `NUMBER`, `LBRACE`...). Os **não terminais** são as regras de parser, escritas em minúscula. Um símbolo é não terminal quando tem regra própria, isto é, quando aparece à esquerda dos dois-pontos.

Não terminais: `programa`, `declaracao`, `unidade`, `arma`, `propriedade`, `equipe`, `batalha`, `instrucao`, `movimento`, `ataque`, `disparo`, `mergulho`, `emersao`, `sonar`, `condicional`, `repeticao`, `bloco`, `comparacao`, `primario` e `numero`. A regra inicial é `programa`.

### 8.2 Regras

Abaixo, a mesma gramática do `.g4` em EBNF: `{ ... }` é repetição (o `*` do ANTLR), `[ ... ]` é opcional (o `?`) e `|` separa alternativas.

```ebnf
programa    = { declaracao | instrucao }, EOF ;
declaracao  = unidade | equipe | batalha ;
unidade     = ("tank" | "submarine" | "aircraft"), IDENTIFIER, "{", { propriedade | arma }, "}" ;
arma        = ("gun" | "torpedo" | "missile"), IDENTIFIER, [ "{", { propriedade }, "}" ] ;
propriedade = IDENTIFIER, numero ;
equipe      = "team", IDENTIFIER, "{", { IDENTIFIER }, "}" ;
batalha     = "battle", IDENTIFIER, "{", IDENTIFIER, "vs", IDENTIFIER, "}" ;

instrucao   = movimento | ataque | disparo | mergulho | emersao
            | sonar | condicional | repeticao ;
movimento   = "move", IDENTIFIER, numero, numero ;
ataque      = "attack", IDENTIFIER, IDENTIFIER ;
disparo     = "fire", IDENTIFIER, IDENTIFIER, IDENTIFIER ;
mergulho    = "dive", IDENTIFIER, numero ;
emersao     = "surface", IDENTIFIER ;
sonar       = "sonar", IDENTIFIER ;
condicional = "if", comparacao, bloco ;
repeticao   = "repeat", NUMBER, bloco ;
bloco       = "{", { instrucao }, "}" ;

comparacao  = primario, ("<" | ">" | "=="), primario ;
primario    = numero | STRING | IDENTIFIER, [ ".", IDENTIFIER ] ;
numero      = NUMBER | FLOAT ;
```

- **Aninhamento:** `bloco` chama `instrucao`, que pode chamar `condicional` ou `repeticao`, que chamam `bloco` de novo. Essa recursão permite blocos dentro de blocos sem limite de profundidade, e é por isso que a sintaxe precisa de uma gramática livre de contexto (e de uma pilha), e não de um autômato finito. Declarações não são instruções e, portanto, não são válidas dentro de blocos.
- **EOF:** a regra inicial termina em `EOF`, então o parser precisa consumir o arquivo inteiro; texto sobrando depois do último comando é erro, e não é ignorado em silêncio.
- **Sem recursão à esquerda:** nenhuma regra começa chamando a si mesma.

### 8.3 Ambiguidade e precedência

Cada condição admite **exatamente uma** comparação entre dois `primario`, e `primario` não contém operadores. Por isso toda entrada válida tem uma única árvore: não existe uma expressão como `2 + 3 * 4` com duas leituras possíveis, e a ordem das alternativas em `comparacao` não muda o resultado. Comparações encadeadas como `1 < 2 < 3` são rejeitadas. O acesso `unidade.propriedade` faz parte de um único `primario` e é resolvido antes da comparação.

`+` e `-` continuam sendo tokens léxicos, mas não aparecem em nenhuma regra. Se a linguagem ganhar aritmética, a ordem das alternativas no `.g4` passará a definir a precedência (`*` e `/` antes de `+` e `-`, e estes antes das comparações).

### 8.4 Como o parser escolhe a alternativa (First e Follow)

O parser olha **um token à frente** para decidir qual alternativa seguir. Isso funciona porque, em cada escolha, as alternativas começam com tokens diferentes (seus conjuntos **First** não têm nada em comum). Quando uma repetição `{ ... }` pode terminar, o parser sai dela ao ver um token do conjunto **Follow**.

| Regra | First (o que pode começar) | Follow (o que pode vir depois) |
|---|---|---|
| `declaracao` | `tank` `submarine` `aircraft` `team` `battle` | First(`declaracao`) ∪ First(`instrucao`) ∪ {`EOF`} |
| `instrucao` | `move` `attack` `fire` `dive` `surface` `sonar` `if` `repeat` | First(`declaracao`) ∪ First(`instrucao`) ∪ {`EOF`, `}`} |
| `bloco` | `{` | igual a Follow(`instrucao`) |
| `propriedade` | `IDENTIFIER` | `IDENTIFIER` `gun` `torpedo` `missile` `}` |
| `arma` | `gun` `torpedo` `missile` | `IDENTIFIER` `gun` `torpedo` `missile` `}` |
| `comparacao` | `NUMBER` `FLOAT` `STRING` `IDENTIFIER` | `{` |
| `primario` | `NUMBER` `FLOAT` `STRING` `IDENTIFIER` | `<` `>` `==` `{` |

- Em `programa`, First(`declaracao`) e First(`instrucao`) são disjuntos: um token basta para saber se vem uma declaração ou uma instrução. A repetição termina ao ver `EOF`.
- Dentro de `unidade`, `IDENTIFIER` indica uma `propriedade`, `gun`/`torpedo`/`missile` indicam uma `arma`, e `}` encerra a repetição.
- Em `arma`, o bloco `{ ... }` é opcional. Depois do nome da arma, `{` abre o bloco; como `{` não está em Follow(`arma`), um token basta para decidir se o bloco existe.
- Em `primario`, a versão anterior desta especificação tinha duas alternativas começando com `IDENTIFIER` (`acesso_propriedade` e `IDENTIFIER`), ou seja, um conflito de First. A regra foi fatorada: depois do `IDENTIFIER`, um `.` indica acesso a propriedade; qualquer token de Follow(`primario`) indica que o primário terminou.

### 8.5 Árvore sintática e AST

`python src/sintatico.py arquivo.tank` mostra a árvore sintática produzida pelo parser ANTLR: os nós internos são as regras e as folhas são os tokens. Para `repeat 2 { if Alpha.hp > 20 { sonar Alpha } }`:

```text
(programa (instrucao (repeticao repeat 2 (bloco { (instrucao (condicional if
  (comparacao (primario Alpha . hp) > (primario (numero 20)))
  (bloco { (instrucao (sonar sonar Alpha)) }))) }))) <EOF>)
```

O parser manual constrói, a partir dos mesmos tokens, uma AST em dicionários e listas aninhados, mantendo os campos `declarations` e `statements` utilizados pelo interpretador. Nós como `IfStatement` e `RepeatStatement` contêm a lista `body`; condições comparativas contêm nós `left` e `right`, com `MemberAccess` para acesso a propriedade. A árvore é construída antes e independentemente da execução.

### 8.6 Exemplos e erros

As linhas abaixo são julgadas apenas pela sintaxe; a primeira só passaria também pela análise semântica (seção 9) se `Tank1` estivesse declarado.

```tankscript
if Tank1.hp > 20 { repeat 2 { sonar Tank1 } } # sintaticamente válido e recursivo
move Tank1 10                                  # inválido: falta a coordenada y
if 1 < 2 < 3 { sonar Tank1 }                   # inválido: comparação encadeada
repeat 1 { tank Tank1 {} }                     # inválido: declaração dentro do bloco
```

Os dois parsers informam linha e coluna. O parser ANTLR usa as mensagens padrão da ferramenta, por exemplo `Linha 1, coluna 10: mismatched input '<' expecting '{'`: o token entre aspas depois de `input` é o que foi encontrado, e o `expecting` diz o que a regra esperava naquele ponto.

Execute os testes do parser com `python -m pytest tests/test_parser.py` e a suíte completa com `python -m pytest`.

## 9. Análise semântica (E4)

A análise semântica está em `tankscript/semantico.py`. Ela percorre a árvore sintática do ANTLR com um *visitor* (a classe `TankScriptParserVisitor`, gerada pela opção `-visitor` do `gerar.sh`) e só roda depois que as análises léxica e sintática terminam sem erro. O `main.py` executa as três fases antes de iniciar o jogo, e `python src/semantico.py arquivo.tank` executa só a verificação.

### 9.1 Tabela de símbolos

A tabela registra cada nome declarado e o que ele significa:

| Categoria | Guarda |
|---|---|
| unidade | tipo (`tank`, `submarine` ou `aircraft`) e armas, com o tipo de cada uma (`gun`, `torpedo` ou `missile`) |
| equipe | unidades que a compõem |
| batalha | nome |

A análise faz duas passagens: primeiro registra todas as declarações (unidades, depois equipes, depois batalhas) e só então verifica as instruções. Por isso uma instrução pode aparecer antes da declaração da unidade que usa, como já acontecia no interpretador, que executa as declarações antes das instruções.

### 9.2 Tipos de unidade e de arma

Os atributos vêm do tipo e estão em `tankscript/catalogo.py`; o interpretador, a análise semântica e a interface web leem a mesma tabela.

| Tipo | hp | armor | speed | radar | sonar | Arma que monta |
|---|---|---|---|---|---|---|
| `tank` | 120 | 15 | 30 | 20 | 30 | `gun` |
| `submarine` | 90 | 10 | 25 | 20 | 40 | `torpedo` |
| `aircraft` | 70 | 5 | 60 | 20 | 40 | `missile` |

`radar` e `sonar` estão em unidades do mapa, em que cada célula mede 10: toda unidade enxerga 2 casas ao redor, e o sonar alcança 3 ou 4 casas. O alcance do sonar não é um atributo consultável, porque `sonar` é palavra reservada.

| Arma | damage | range | ammo | cooldown |
|---|---|---|---|---|
| `gun` | 40 | 60 | 6 | 1 |
| `torpedo` | 70 | 80 | 3 | 2 |
| `missile` | 55 | 100 | 2 | 2 |

Cada unidade monta no máximo 2 armas. Nas condições, `unidade.propriedade` aceita `hp`, `armor`, `speed`, `radar`, `depth`, `x` e `y`, e sempre tem tipo número.

### 9.3 Regras

**Nomes**

- Unidade, equipe e batalha não podem ser declaradas duas vezes com o mesmo nome; uma arma não pode se repetir dentro da mesma unidade.
- Toda unidade usada em instrução, equipe ou condição precisa estar declarada.
- Uma unidade aparece no máximo uma vez em uma equipe, e pertence a no máximo uma equipe.
- A batalha só pode citar equipes declaradas, e uma equipe não enfrenta a si mesma.
- Em `fire`, a arma precisa pertencer ao atacante; em `attack`, o atacante precisa ter pelo menos uma arma.
- `dive` e `surface` só valem para submarinos, e a profundidade do `dive` precisa ser maior que 0.
- Em `fire` e `attack`, o alvo não pode ser o próprio atacante nem uma unidade da mesma equipe.

**Tipos**

- Os atributos são fixos: qualquer propriedade escrita numa unidade ou arma é erro. Se o atributo existe, a mensagem informa o valor do tipo (`'hp' é fixo: todo tank tem hp 120`); se não existe, lista os atributos do tipo.
- Cada tipo de unidade só monta a sua arma (tabela 9.2), e uma unidade tem no máximo 2 armas.
- `<` e `>` comparam dois números; `==` compara dois valores do mesmo tipo (número com número, texto com texto).
- Um identificador sozinho não tem valor numa condição, pois a linguagem não tem variáveis: use `unidade.propriedade`.

### 9.4 Mensagens

Ao contrário da análise sintática, que para no primeiro erro, a análise semântica relata **todos** os erros encontrados, em ordem de posição, cada um com linha e coluna:

```text
$ python src/semantico.py examples/invalidos_semanticos/arma_de_outra_unidade.tank
Erro semântico: Linha 8, coluna 13: 'Falcon' não possui a arma 'T1'
1 erro(s) semântico(s)
```

Os exemplos em `examples/invalidos_semanticos/` estão corretos léxica e sintaticamente e falham só nesta fase.

### 9.5 Regras extras da arena (interface web)

A interface web (`src/servidor.py`) usa a mesma análise, com regras a mais definidas em `tankscript/partida.py`:

- O `cenario.tank` só declara unidades. Equipes, batalha e instruções são erro, porque o jogo monta a equipe `Jogador`, gera a frota da equipe `Inimigo` em TankScript e declara a batalha.
- O exército custa no máximo 20 pontos: `tank` 4, `submarine` 5, `aircraft` 4, e cada arma além da primeira mais 1. O inimigo gasta o mesmo orçamento.
- O `turno.tank` só tem instruções, e cada instrução só pode comandar unidades do jogador.
- As coordenadas de `move` precisam estar dentro do mapa: x de 0 a 199 e y de 0 a 99.
- Durante a execução, um `if` que lê uma unidade inimiga fora de vista conta como falso, e o navegador não recebe a posição, a vida nem as armas de inimigos na névoa.
- A partida termina em vitória quando uma equipe é destruída, e em empate quando nenhum lado consegue mais ferir o outro ou ao chegar a 50 turnos.
