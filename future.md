# 🚀 TankIO — Future Implementations & Roadmap (Full Specification)

Este documento apresenta o plano detalhado de expansão para a linguagem **TankScript** e para a engine de simulação **TankIO**. O objetivo é transformar a arquitetura num sistema tático avançado com suporte a maior expressiveness sintática, IA adaptativa, visualização rica e multijogador.

---

## 🏗️ 1. Expansão da Linguagem (DSL & Compilador)

### 1.1. Suporte a Variáveis e Aritmética
Atualmente a DSL suporta apenas valores numéricos literais. A próxima fase adicionará um ambiente de símbolos (*Symbol Table*) dinâmico:
- **Declaração de Variáveis:**
  let target_x = 80
  let target_y = 50
  let default_depth = 30

- **Expressões Aritméticas Completas:** Suporte a operações com precedência matemática (+, -, *, /):
  move Tiger1 (target_x + 10) (target_y * 2)

### 1.2. Estruturas de Repetição Dinâmicas
- **Laço `while`:**
  while Shark1.hp > 0 {
      fire Tiger1 Cannon Shark1
  }

- **Laço `for` Iterativo:**
  for i in range(1, 4) {
      move Tiger1 (i * 20) 20
  }

### 1.3. Procedimentos e Funções (`fn`)
Suporte a rotinas reaproveitáveis com passagem de parâmetros:
  fn tactical_retreat(unit, safe_x, safe_y) {
      move unit safe_x safe_y
      sonar unit
  }

  # Chamada do procedimento
  tactical_retreat(Tiger1, 10, 10)

### 1.4. Análise Semântica & Validação de Tipos (Type Checking)
- **Verificação Estrita:** Impedir a atribuição de armas incompatíveis no momento do parsing (ex: impedir a adição de um torpedo num tank).
- **Escopo e Referências:** Alertar em tempo de compilação se um comando fizer referência a uma unidade ou arma não declarada na AST.

---

## 🎮 2. Novas Mecânicas de Jogo & Motor Tático

### 2.1. Novas Classes de Unidades

| Classe | Tipo | Habilidade Especial |
| :--- | :--- | :--- |
| **`drone`** | Aéreo | Voa sobre qualquer obstáculo (`I`), sem sofrer colisão. Possui alcance de radar expandido ($2\times$). |
| **`repair_tank`** | Terrestre / Suporte | Não possui armas de alto dano, mas executa a ação `repair` para restaurar HP de aliados próximos. |
| **`corvette`** | Aquático | Navio de superfície rápido com cargas de profundidade (*Depth Charges*) capazes de acertar submarinos submersos. |

### 2.2. Terrenos Dinâmicos e Interativos
- **Destruição de Cobertura (`#`):** Estruturas de cobertura podem ser destruídas caso recebam uma quantidade $N$ de dano acumulado, convertendo-se em terreno aberto (`.`).
- **Minas Terrestres e Aquáticas (`mine`):**
  plant_mine Tiger1 40 40
  *(Unidades que passarem sobre uma mina oculta sofrem dano massivo imediato).*

### 2.3. Sistema Climatológico e Eventos Globais
- **Neblina Densa:** Reduz o raio de radar de todas as unidades em $50\%$ por um período de $N$ turnos.
- **Tempestade Marítima:** Submarinos enfrentam consumo de movimento dobrado e instabilidade nos torpedos (chance de falha/desvio).

### 2.4. Gestão Avançada de Recursos
- **Pontos de Reabastecimento (Supply Depots):** Posições estratégicas no mapa onde unidades podem repor munição (`ammo`) e reparar armadura (`armor`).

---

## 🤖 3. Inteligência Artificial (IA) Avançada

### 3.1. Algoritmo de Pathfinding (A*)
Substituição da movimentação em linha reta da IA por um algoritmo de busca de caminhos **A*** (A-Star), permitindo que bots se desviem autonomamente de montanhas (`I`) e busquem posições de cobertura (`#`).

### 3.2. Árvores de Decisão e Comportamento
- **Perfil Agressivo:** Foca no travamento de alvo no inimigo com menor HP e avanço rápido.
- **Perfil Furtivo / Emboscada:** Utiliza submarinos para disparar submerso, recuar imediatamente para a névoa e alterar de posição após o disparo.
- **Perfil Defensivo:** Mantém unidades em posições de ruínas (`#`), priorizando o uso de `sonar` e contra-ataques de longo alcance.

---

## 🎨 4. Interface, Renderização & DX

### 4.1. Visualização em Pygame (Interface Gráfica 2D)
Desenvolvimento de uma camada de renderização gráfica opcional em **Pygame**:
- *Sprites* animados para tanques, submarinos e explosões.
- Shader/overlay visual dinâmico para a Névoa de Guerra (Fog of War).
- Exibição de barras de HP, tempo de recarga (*cooldown*) e trajetórias de projéteis em tempo real.

### 4.2. Developer Experience (DX) & Extensão VS Code
- **Sintaxe Highlighting:** Lançamento de um pacote `.vsix` para coloração de código dos ficheiros `.tank`.
- **Linter Integrado:** Indicação precisa no terminal de erros de sintaxe e semântica com número da linha, coluna e contexto visual:
  Error [Line 12, Col 5]: Invalid weapon 'Laser' assigned to unit 'Tiger1'.
  12 |   gun Laser {
     |       ^^^^^ Subtype not supported.

---
