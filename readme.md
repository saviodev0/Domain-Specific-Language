# 🛡️ TankIO — Tactical Game & TankScript DSL

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Docker](https://img.shields.io/badge/Docker-Supported-blue)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-orange)

O **TankIO** é um jogo de simulação tática por turnos, executado no terminal e controlado por uma linguagem específica de domínio própria, a **TankScript**. Um programa TankScript declara unidades, armas, equipes e ordens iniciais; o TankIO interpreta essas ordens e conduz a partida.

O projeto implementa as fases de um compilador/interpretador (lexer, parser, árvore sintática, análise semântica e interpretador) integradas a um motor de jogo com névoa de guerra, terrenos táticos e combate entre tanques e submarinos.

## Funcionalidades

- **Linguagem própria (`.tank`):** declaração de unidades, armas, equipes, condições (`if`) e repetições (`repeat`).
- **Névoa de guerra e sonar:** cada unidade tem raio de visão. O comando `sonar` revela unidades ocultas e submersas.
- **Terrenos:**
  - `I` (ilha): bloqueia o movimento.
  - `#` (ruínas): reduz o dano recebido em 50%.
  - `~` (água rasa): impede a submersão de submarinos.
- **Gerenciamento tático:** munição (`ammo`), tempo de recarga (`cooldown`) e estados especiais dos submarinos.
- **Modo interativo com IA:** partida por turnos contra um adversário controlado pelo computador.

## A linguagem

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

O cenário completo está em `examples/espiral.tank`. A sintaxe, a gramática e as decisões da linguagem estão em [docs/especificacao.md](docs/especificacao.md).

## Arquitetura

```text
arquivo .tank
     │
     ▼
 Lexer (ANTLR, TankScriptLexer.g4)        caracteres → tokens; descarta espaços e comentários '#'
     │
     ├──▶ Parser ANTLR (TankScriptParser.g4)   tokens → árvore sintática (src/sintatico.py)
     │         │
     │         ▼
     │    Análise semântica (visitor)       nomes declarados e tipos (src/semantico.py)
     │
     ▼
 Parser manual (tankscript/parser.py)      tokens → AST em dicionários e listas
     │
     ▼
 Interpreter                                regras de movimento, dano e colisão
     ├──▶ GridRenderer                      grade ASCII e névoa de guerra
     └──▶ EnemyAI                           ações do adversário
```

Os dois parsers reconhecem a mesma linguagem; os testes conferem que aceitam e rejeitam os mesmos programas. O jogo só inicia se o cenário passar pelas análises léxica, sintática e semântica. O código ANTLR é gerado em `gerado/`, que não é versionado.

## Como executar

### Com Docker

```sh
docker build -f docker/Dockerfile -t tankio .
docker run -it --rm tankio
```

O parâmetro `-it` é necessário para o teclado chegar ao terminal do contêiner. A imagem já gera o lexer e o parser durante o build.

### Localmente

Requisitos: Python 3.10 ou superior e Java 11 ou superior. O `antlr4-tools` oferece instalar o Java na primeira execução, caso ele não esteja disponível.

```sh
git clone https://github.com/saviodev0/Domain-Specific-Language.git
cd Domain-Specific-Language
python -m pip install -r requirements.txt -r requirements-antlr.txt
sh gerar.sh
python main.py
```

O `gerar.sh` gera o lexer e o parser com o ANTLR **4.13.2**, a mesma versão do runtime. Execute-o de novo sempre que alterar um arquivo `.g4`.

No Windows PowerShell, substitua `sh gerar.sh` por:

```powershell
$env:ANTLR4_TOOLS_ANTLR_VERSION = "4.13.2"
$scripts = (python -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))").Trim()
$antlr4 = Join-Path $scripts "antlr4.exe"
New-Item -ItemType Directory -Force gerado | Out-Null
& $antlr4 -Dlanguage=Python3 -visitor -Xexact-output-dir -o gerado -lib gerado tankscript\TankScriptLexer.g4 tankscript\TankScriptParser.g4
```

## Ferramentas de linha de comando

Listar os tokens de um programa (análise léxica):

```sh
python src/lexico.py examples/ola.tank
```

Mostrar a árvore sintática de um programa (análise sintática):

```sh
python src/sintatico.py examples/espiral.tank
```

Testar uma regra da gramática isoladamente, sem gerar código (digite a entrada e encerre com Ctrl+D):

```sh
antlr4-parse tankscript/TankScriptLexer.g4 tankscript/TankScriptParser.g4 instrucao -tree
```

Verificar nomes e tipos (análise semântica):

```sh
python src/semantico.py examples/espiral.tank
```

Erros léxicos e sintáticos informam linha, coluna, o que foi encontrado e o que era esperado, por exemplo:

```text
Erro: Linha 1, coluna 10: mismatched input '<' expecting '{'
```

A análise semântica relata todos os erros de nome e de tipo de uma vez, por exemplo:

```text
Erro semântico: Linha 5, coluna 6: unidade 'Ghost' não declarada
```

## Testes

Com o código ANTLR já gerado:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest
```

Para rodar apenas os testes do parser e da gramática, use `python -m pytest tests/test_parser.py`; para a análise semântica, `python -m pytest tests/test_semantico.py`.

## Documentação

- [docs/especificacao.md](docs/especificacao.md): especificação da TankScript, gramática, First e Follow, e regras semânticas.
- [documentation.md](documentation.md): regras do jogo TankIO.
- [future.md](future.md): planos de expansão.
- [DIARIO.md](DIARIO.md): diário de desenvolvimento das entregas.
