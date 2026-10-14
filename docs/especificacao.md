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