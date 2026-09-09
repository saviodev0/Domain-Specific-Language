# TankScript

Uma linguagem simples para criar batalhas com **tanques e submarinos**.

## 1. Exemplo básico

```tank
tank Tiger {
    hp 100
    armor 50
    speed 40
}

submarine Shark {
    hp 80
    armor 30
    speed 25
    depth 100
}
```

---

## 2. Armas

```tank
tank Tiger {
    hp 100
    armor 50

    gun Cannon {
        damage 30
        range 500
    }
}
```

Submarino:

```tank
submarine Shark {
    hp 80

    torpedo T1 {
        damage 50
        range 800
    }
}
```

---

## 3. Movimento

```tank
move Tiger 100 200
```

O formato é:

```text
move unidade x y
```

---

## 4. Ataque

```tank
attack Tiger Shark
```

Significa:

```text
Tiger ataca Shark
```

---

## 5. Disparo

```tank
fire Tiger Cannon Shark
```

Formato:

```text
fire tanque arma alvo
```

---

## 6. Submarinos

Submarinos possuem uma operação especial:

```tank
dive Shark 100
```

E para voltar à superfície:

```tank
surface Shark
```

---

## 7. Condições

A linguagem pode ter apenas `if` inicialmente:

```tank
if Tiger.hp < 30 {
    move Tiger 0 0
}
```

---

## 8. Equipes

```tank
team Blue {
    Tiger
}

team Red {
    Shark
}
```

---

## 9. Batalha

Uma batalha pode ser extremamente simples:

```tank
battle War {
    Blue vs Red
}
```

---

# 10. Sintaxe completa inicial

A primeira versão da linguagem pode ter somente estas palavras:

```text
tank
submarine
gun
torpedo

hp
armor
speed
damage
range
depth

team
battle

move
attack
fire
dive
surface

if
```

Isso já é suficiente para criar uma primeira versão funcional do compilador.

---

# 11. Léxico

Os tokens principais seriam:

```text
IDENTIFIER
NUMBER
STRING

{
}
 
+ 
-
<
>
==
```

Palavras reservadas:

```text
tank
submarine
gun
torpedo
team
battle
move
attack
fire
dive
surface
if
```

---

# 12. Gramática pequena

Uma gramática inicial poderia ser:

```ebnf
program = { declaration } ;

declaration =
      tank
    | submarine
    | team
    | battle ;

tank =
    "tank" identifier "{" { property | weapon } "}" ;

submarine =
    "submarine" identifier "{" { property | weapon } "}" ;

weapon =
      "gun" identifier "{" { property } "}"
    | "torpedo" identifier "{" { property } "}" ;

property =
      identifier number ;

team =
    "team" identifier "{" { identifier } "}" ;

battle =
    "battle" identifier "{" identifier "vs" identifier "}" ;

statement =
      move
    | attack
    | fire
    | dive
    | surface
    | if ;

move =
    "move" identifier number number ;

attack =
    "attack" identifier identifier ;

fire =
    "fire" identifier identifier identifier ;

dive =
    "dive" identifier number ;

surface =
    "surface" identifier ;

if =
    "if" expression "{" { statement } "}" ;
```

---

# 13. Exemplo de programa inteiro

```tank
tank Tiger {
    hp 100
    armor 50
    speed 40

    gun Cannon {
        damage 30
        range 500
    }
}

submarine Shark {
    hp 80
    armor 30
    speed 25
    depth 100

    torpedo T1 {
        damage 50
        range 800
    }
}

team Blue {
    Tiger
}

team Red {
    Shark
}

battle War {
    Blue vs Red
}

move Tiger 100 100
dive Shark 80
fire Tiger Cannon Shark
attack Shark Tiger
```

---

# 14. Ideia do compilador

O compilador pode ser pequeno:

```text
TankScript
    ↓
Lexer
    ↓
Parser
    ↓
AST
    ↓
Validador
    ↓
IR
    ↓
Motor da batalha
```

Na primeira versão, **não é necessário criar uma linguagem enorme**.

O objetivo pode ser primeiro fazer isto funcionar:

```tank
tank Tiger {
    hp 100
}

move Tiger 10 20
```

Depois adicionar:

```tank
fire Tiger Cannon Shark
```

E posteriormente:

```tank
if Tiger.hp < 30 {
    move Tiger 0 0
}
```

Assim você consegue construir o compilador passo a passo sem deixar a sintaxe complicada.
