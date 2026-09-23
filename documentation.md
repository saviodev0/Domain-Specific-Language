# 🛡️ TankIO — Arena Tactical Simulator & TankScript DSL

O **TankIO** é um jogo de simulação tática baseado em turnos que utiliza uma Linguagem de Domínio Específico (**DSL**) própria, chamada **TankScript**. O jogo combina elementos de estratégia por turnos, gestão de munições, névoa de guerra, utilização de terreno tático e combate entre veículos blindados e submarinos.

---

## 🗺️ 1. O Mapa e Elementos de Terreno

O campo de batalha é representado numa grelha bidimensional com coordenadas de $0$ a $190$ no eixo $X$ e $0$ a $90$ no eixo $Y$.

### Legenda de Símbolos

| Símbolo | Nome | Descrição |
| :---: | :--- | :--- |
| **`T`** | **Tanque** | Unidade terrestre blindada. |
| **`S`** | **Submarino** | Unidade aquática (superfície ou submerso `~S~`). |
| **`I`** | **Ilha / Montanha** | **Obstáculo Inabalável:** Bloqueia movimentação. Tentativas de atravessar geram aviso de colisão. |
| **`#`** | **Ruínas / Cobertura** | **Posição Defensiva:** Unidades posicionadas aqui recebem **50% a menos de dano** de ataques. |
| **`~`** | **Água Rasa** | **Zona Restrita:** Submarinos em água rasa **não podem submergir** (`dive`). |
| **`?`** | **Névoa de Guerra** | **Célula Oculta:** Áreas fora do alcance de radar das tuas unidades ou de pulso de sonar. |
| **`.`** | **Terreno Aberto** | Solo ou água comum sem modificadores. |

---

## 🌫️ 2. Névoa de Guerra & Deteção

1. **Visão Passiva (Radar):** Toda a unidade possui um raio de radar definido (`radar`). Áreas dentro do seu raio revelam o mapa em tempo real.
2. **Furtividade de Submarinos:** Submarinos submersos (`depth > 0`) pertencentes à equipa inimiga ficam **totalmente invisíveis**, a menos que sejam detetados por Sonar ou tenham atacado no turno anterior.
3. **Mecânica do Sonar:** O comando `sonar` emite um pulso que revela unidades num raio expandido ($1.5\times$) durante 2 turnos, ignorando a furtividade de submersão.

---

## ⚔️ 3. Regras de Combate e Mecânicas

### Modificadores de Dano
* **Ataque Padrão:** $\text{Dano Real} = \text{Dano da Arma} - \text{Armadura do Alvo}$.
* **Cobertura (`#`):** Se o alvo estiver numa cobertura, o dano final sofre redução de **50%**.
* **Submarino Exposto (Crítico!):** Se um submarino ataca enquanto está submerso, ele é obrigado a emergir no turno seguinte, ficando no estado **EXPOSTO**. Ataques sofridos enquanto exposto causam **Dano Duplo ($2\times$)**.
* **Imunidade Submersa:** Canhões convencionais (`gun`) **não causam dano** a submarinos submersos (`depth > 0`).

### Munição e Cooldown
* **Munição (`ammo`):** Cada arma possui uma quantidade limitada de tiros. Quando atinge $0$, a arma fica inoperante.
* **Recarga / Cooldown (`cooldown`):** Após disparar uma arma, ela entra em tempo de recarga por $N$ turnos.

---

## 💻 4. Guia de Comandos no CLI (Console)

Durante a tua jogada, podes inserir os seguintes comandos interativos no terminal:

| Comando | Exemplo | Descrição |
| :--- | :--- | :--- |
| **Mover** | `move Tiger1 50 50` | Move a unidade para as coordenadas $(X, Y)$. |
| **Disparar** | `fire Tiger1 Cannon Shark1` | Ataca o alvo com a arma especificada. |
| **Submergir** | `dive Shark1 40` | Faz o submarino submergir para a profundidade informada. |
| **Emergir** | `surface Shark1` | Traz o submarino de volta à superfície ($0\text{m}$). |
| **Sonar** | `sonar Tiger1` | Emite um pulso de radar para revelar a névoa e unidades submersas. |
| **Sair** | `exit` | Encerra a simulação. |

---

## 📜 5. Sintaxe da DSL (TankScript)

O ficheiro de cenário `.tank` permite declarar unidades, equipas e ordens iniciais:

```tankscript
# Declaração de um Tanque
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

# Declaração de um Submarino
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

# Organização das Equipas
team Blue {
    Tiger1
}

team Red {
    Shark1
}

battle War {
    Blue vs Red
}

# Posições e Ações Iniciais
move Tiger1 20 20
move Shark1 170 80
dive Shark1 40