# 🛡️ TankIO — Tactical Game & TankScript DSL

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Docker](https://img.shields.io/badge/Docker-Supported-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-orange)

O **TankIO** é um jogo de simulação tática baseado em turnos executado no terminal, movido por uma Linguagem de Domínio Específico (**DSL**) própria chamada **TankScript**. O projeto demonstra a construção completa de um compilador/interpretador (Lexer, Parser, AST e Interpretador) integrado a um motor de jogo com suporte a névoa de guerra, terrenos táticos e combate entre tanques e submarinos.

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

#### Passo a Passo

1. Clona o repositório:
   git clone https://github.com/teu-usuario/Domain-Specific-Language.git
   cd Domain-Specific-Language

2. Limpa a cache do Python (opcional, recomendado para garantir atualizações):
   - Windows (PowerShell):
     Remove-Item -Recurse -Force tankscript\__pycache__
   - Linux/macOS:
     rm -rf tankscript/__pycache__

3. Inicia a aplicação:
   python main.py

---

## 🕹️ Comandos do CLI

Durante o teu turno no terminal, podes executar as seguintes ações:

| Comando | Exemplo | Descrição |
| :--- | :--- | :--- |
| `move` | `move Tiger1 50 50` | Move a unidade para a coordenada (X, Y). |
| `fire` | `fire Tiger1 Cannon Shark1` | Dispara com a arma especificada contra o alvo. |
| `dive` | `dive Shark1 40` | Faz o submarino submergir N metros. |
| `surface` | `surface Shark1` | Traz o submarino de volta à superfície. |
| `sonar` | `sonar Tiger1` | Emite um pulso para revelar áreas cobertas pela névoa. |
| `exit` | `exit` | Encerra a partida. |

---

## 📝 Exemplo de Código em TankScript (`.tank`)

# Declaração do Tanque do Jogador
tank Tiger1 {
    hp 100
    armor 30
    speed 40
    radar 70
    gun Cannon {
        damage 50
        range 500
        ammo 5
        cooldown 1
    }
}

# Declaração do Submarino Inimigo
submarine Shark1 {
    hp 80
    armor 10
    speed 25
    radar 90
    torpedo T1 {
        damage 70
        range 800
        ammo 3
        cooldown 2
    }
}

# Definição de Equipas
team Blue {
    Tiger1
}

team Red {
    Shark1
}

battle War {
    Blue vs Red
}

# Posições Iniciais
move Tiger1 20 20
move Shark1 170 80
dive Shark1 40

---

## 📚 Documentação Complementar

- `TankIO.md` — Especificação completa das regras de jogo e sintaxe.
- `FUTURE_FEATURES.md` — Planeamento das próximas versões e novas funcionalidades.
- `documentation.md` - Documentação de como usar cada funcionalidade.