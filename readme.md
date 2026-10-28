# 🛡️ TankIO — Tactical Game & TankScript DSL

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Docker](https://img.shields.io/badge/Docker-Supported-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-orange)

O **TankIO** é um jogo de simulação tática baseado em turnos executado no terminal, movido por uma Linguagem de Domínio Específico (**DSL**) própria chamada **TankScript**. O projeto demonstra a construção completa de um compilador/interpretador (Lexer, Parser, AST e Interpretador) integrado a um motor de jogo com suporte a névoa de guerra, terrenos táticos e combate entre tanques e submarinos. Muito divertida

---

## 📸 Funcionalidades Principais

- **Linguagem Customizada (`.tank`):** Declaração de unidades, armas, equipas, condições (`if`) e repetições (`repeat`).
- **Névoa de Guerra & Sonar:** Unidades possuem raio de visão. O comando `sonar` lança um pulso que revela unidades ocultas e submersas.
- **Mecânica de Terrenos:**
  - `I` (Ilhas): Bloqueiam o movimento (colisão).
  - `#` (Ruínas): Oferecem posição defensiva com 50% de redução de dano.
  - `~` (Água Rasa): Impede a submersão de submarinos.
- **Gerenciamento Tático:** Sistema de munição (`ammo`), tempo de recarga (`cooldown`) e estados especiais (submarinos submersos ou expostos a dano duplo).
- **CLI Interativo & IA:** Modo de jogo por turnos contra uma Inteligência Artificial no terminal.

---

## 🛠️ Arquitetura do Sistema

  Ficheiro .tank / CLI
           │
           ▼
     ┌───────────┐
     │   Lexer   │  <-- Converte o código em Tokens (ignora comentários '#')
     └─────┬─────┘
           │
           ▼
     ┌───────────┐
     │  Parser   │  <-- Valida a sintaxe EBNF e constrói a AST
     └─────┬─────┘
           │
           ▼
     ┌───────────┐
     │    AST    │  <-- Árvore de Sintaxe Abstrata
     └─────┬─────┘
           │
           ▼
 ┌───────────────────┐
 │   Interpreter     │  <-- Processa lógica, regras de dano e colisões
 └─────────┬─────────┘
           │
           ├──> GridRenderer (Renderiza a grelha ASCII e a Névoa)
           └──> EnemyAI     (Executa as ações do bot adversário)

---

## 🚀 Como Executar

### Opção 1: Via Docker (Recomendado)

Não precisas de instalar o Python localmente, apenas o Docker:

1. Constroi a imagem usando o Dockerfile na pasta `docker/`:
   docker build -f docker/Dockerfile -t tankio .

2. Executa o jogo no modo interativo:
   docker run -it --rm tankio

*(O parâmetro `-it` é obrigatório para ligar o teu teclado ao terminal do container).*

---

### Opção 2: Localmente via Python

#### Pré-requisitos
- Python 3.10 ou superior instalado.
- Java 11 ou superior para regenerar o lexer ANTLR.

#### Passo a Passo

1. Clona o repositório:
# TankIO e TankScript

TankScript é uma linguagem específica para descrever batalhas táticas entre tanques e submarinos. O programa declara unidades, armas, equipas e ordens iniciais; o TankIO interpreta essas ordens no jogo.

## 1. A linguagem

Este exemplo declara um tanque e sua posição inicial. O cenário completo está em `examples/espiral.tank`.

```tankscript
# Define o tanque e suas propriedades.
tank Falcon {
    hp 100
    armor 20
    speed 35
    radar 60.5
}

# Define a posição inicial.
move Falcon 20 20
```

A sintaxe e as decisões da linguagem estão em [docs/especificacao.md](docs/especificacao.md).

## 2. Instalação e execução

Requisitos locais: Python 3.10 ou superior e Java 11 ou superior para gerar o lexer e o parser ANTLR. O código gerado não é versionado; gere-o antes de iniciar o jogo ou executar os testes.

```sh
python -m pip install -r requirements.txt
python -m pip install -r requirements-antlr.txt
sh gerar.sh
python main.py
```

Para listar os tokens de um arquivo TankScript:

```sh
python src/lexico.py examples/ola.tank
```

Para preparar o ambiente de desenvolvimento e os testes:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest
```

ANTLR e runtime usados: **4.13.2**. Para regenerar a gramática após alterá-la, execute `sh gerar.sh` novamente.

No Windows PowerShell, gere o lexer com:

```powershell
$env:ANTLR4_TOOLS_ANTLR_VERSION = "4.13.2"
$scripts = (python -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))").Trim()
$antlr4 = Join-Path $scripts "antlr4.exe"
New-Item -ItemType Directory -Force gerado | Out-Null
& $antlr4 -Dlanguage=Python3 -visitor -Xexact-output-dir -o gerado -lib gerado tankscript\TankScriptLexer.g4 tankscript\TankScriptParser.g4
```

## 3. Análise sintática (E3)

A gramática sintática está em `tankscript/TankScriptParser.g4`, com regras de parser em minúscula e a regra inicial `programa` terminando em `EOF`. Para ver a árvore sintática de um programa:

```sh
python src/sintatico.py examples/espiral.tank
```

Para testar uma regra isolada enquanto edita a gramática, sem gerar código (digite a entrada e encerre com Ctrl+D):

```sh
antlr4-parse tankscript/TankScriptLexer.g4 tankscript/TankScriptParser.g4 instrucao -tree
```

Os mesmos tokens também são consumidos pelo parser manual em Python (`tankscript/parser.py`), que reconhece a mesma linguagem e monta a AST usada pelo jogo. O parser reconhece declarações e instruções, valida o fechamento dos blocos e monta uma AST em dicionários/listas compatível com o interpretador. Os blocos `if` e `repeat` são recursivos; as condições aceitam uma comparação (`<`, `>` ou `==`) entre valores primários ou acessos `unidade.propriedade`. A gramática completa e as decisões estão em [docs/especificacao.md](docs/especificacao.md).

## 4. Testes

Instale as dependências e gere o lexer antes de executar os testes:

```powershell
python -m pip install -r requirements.txt -r requirements-antlr.txt -r requirements-dev.txt
# Gere o lexer usando o comando PowerShell da seção anterior.
python -m pytest tests/test_parser.py -q
python -m pytest -q
```

O primeiro comando de testes valida gramática e AST; o segundo executa toda a suíte, incluindo lexer e exemplos da E2. Para reproduzir um erro sintático com o parser:

```sh
python -c "from tankscript import Lexer, Parser; Parser(Lexer('move Falcon 20').tokenize()).parse()"
```

O erro informa linha, coluna, token encontrado e o elemento esperado.

## Docker

```sh
docker build -f docker/Dockerfile -t tankio .
docker run -it --rm tankio
```