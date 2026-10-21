# Especificação da TankScript

## 1. Finalidade

TankScript é uma linguagem específica para descrever cenários de batalhas táticas entre tanques e submarinos. Um programa declara unidades, armas, equipas e ordens iniciais que o TankIO interpreta para iniciar uma partida.

## 2. Programa completo de exemplo

```tankscript
# Declara um tanque terrestre.
tank Tiger1 {
    # Define pontos de vida inteiros.
    hp 100
    # Define a armadura inteira.
    armor 30
    # Define a velocidade inteira.
    speed 40
    # O radar aceita valores reais.
    radar 70.5
    # Declara um canhão chamado Cannon.
    gun Cannon {
        # Define o dano inteiro do canhão.
        damage 50
        # Define o alcance inteiro do canhão.
        range 500
        # Define a munição inicial.
        ammo 5
        # Define a recarga em turnos.
        cooldown 1
    }
}
# Declara um submarino.
submarine Shark1 {
    # Define os pontos de vida.
    hp 80
    # Define a armadura.
    armor 10
    # Define a velocidade.
    speed 25
    # Define o alcance do radar.
    radar 90
    # Declara um torpedo chamado T1.
    torpedo T1 {
        # Define o dano do torpedo.
        damage 70
        # Define o alcance do torpedo.
        range 800
        # Define a munição inicial.
        ammo 3
        # Define a recarga em turnos.
        cooldown 2
    }
}
# Coloca o tanque na equipa Azul.
team Blue {
    Tiger1
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
move Shark1 170 80
# Define a profundidade inicial do submarino.
dive Shark1 40
# Executa sonar quando a condição textual for verdadeira.
if "ready" == "ready" {
    sonar Tiger1
}
```

## 3. Tipos de dado

- **Inteiro:** sequência de dígitos, como `100`.
- **Real:** dígitos, ponto decimal e ao menos um dígito em cada lado, como `70.5`.
- **Texto:** conteúdo entre aspas simples ou duplas, sem quebra de linha. A barra invertida pode escapar um caractere; o valor é preservado sem decodificação de escapes.
- **Identificador:** começa com letra ASCII ou sublinhado e pode continuar com letras, dígitos ou sublinhados, como `Tiger1`.

## 4. Comandos

Declarações: `tank`, `submarine`, `gun`, `torpedo`, `team` e `battle`.

Instruções: `move unidade x y`, `attack atacante alvo`, `fire atacante arma alvo`, `dive unidade profundidade`, `surface unidade`, `sonar unidade`, `if condição { ... }` e `repeat quantidade { ... }`.

Propriedades de unidades e armas são escritas como identificador seguido por número, por exemplo `hp 100` ou `radar 70.5`.

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

O lexer ANTLR entrega tokens ao parser manual em Python (`tankscript/parser.py`). A gramática abaixo descreve a sintaxe reconhecida pelo parser; `{ ... }` representa repetição, `[ ... ]` representa opcionalidade e `|` representa alternativas:

```ebnf
programa       = { declaracao | instrucao }, EOF ;
declaracao     = unidade | equipe | batalha ;
unidade        = ("tank" | "submarine"), IDENTIFICADOR, "{",
                 { propriedade | arma }, "}" ;
arma           = ("gun" | "torpedo"), IDENTIFICADOR, "{",
                 { propriedade }, "}" ;
propriedade    = IDENTIFIER, (NUMBER | FLOAT) ;
equipe         = "team", IDENTIFIER, "{", { IDENTIFIER }, "}" ;
batalha        = "battle", IDENTIFIER, "{", IDENTIFIER, "vs", IDENTIFIER, "}" ;

instrucao      = movimento | ataque | disparo | mergulho | emersao
               | sonar | condicional | repeticao ;
movimento      = "move", IDENTIFIER, numero, numero ;
ataque         = "attack", IDENTIFIER, IDENTIFIER ;
disparo        = "fire", IDENTIFIER, IDENTIFIER, IDENTIFIER ;
mergulho       = "dive", IDENTIFIER, numero ;
emersao        = "surface", IDENTIFIER ;
sonar          = "sonar", IDENTIFIER ;
condicional    = "if", comparacao, "{", { instrucao }, "}" ;
repeticao      = "repeat", NUMBER, "{", { instrucao }, "}" ;
comparacao     = primario, ("<" | ">" | "=="), primario ;
primario       = numero | STRING | acesso_propriedade | IDENTIFIER ;
acesso_propriedade = IDENTIFIER, ".", IDENTIFIER ;
numero         = NUMBER | FLOAT ;
```

Os blocos de `if` e `repeat` são recursivos: podem conter qualquer instrução, inclusive outros blocos. Declarações não são instruções e, portanto, não são válidas dentro desses blocos. As três comparações têm a mesma precedência e cada condição admite exatamente uma comparação; o acesso `unidade.propriedade` é reconhecido como um único primário, sem ambiguidade com o operador de comparação. `+` e `-` continuam sendo tokens léxicos, mas não são aceitos pela gramática sintática.

O parser constrói a AST como dicionários e listas aninhados, mantendo os campos `declarations` e `statements` utilizados pelo interpretador. Nós como `IfStatement` e `RepeatStatement` contêm a lista `body`; condições comparativas contêm nós `left` e `right`, com `MemberAccess` para acesso a propriedade. A árvore é construída antes e independentemente da execução.

Exemplos:

```tankscript
if Tank1.hp > 20 { repeat 2 { sonar Tank1 } } # válido e recursivo
move Tank1 10                                  # inválido: falta a coordenada y
if 1 < 2 < 3 { sonar Tank1 }                   # inválido: comparação encadeada
repeat 1 { tank Tank1 {} }                     # inválido: declaração dentro do bloco
```

Execute os testes do parser com `python -m pytest tests/test_parser.py` e a suíte completa com `python -m pytest`.