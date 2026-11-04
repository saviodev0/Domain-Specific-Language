"""IA da equipe inimiga.

A IA só enxerga o que o radar das suas unidades alcança. Para procurar unidades escondidas na névoa,
ela adapta o mapa de calor por simulação de Monte Carlo do projeto battleships_ai, de DataSnaek,
hoje mitchelljy no GitHub (https://github.com/mitchelljy/battleships_ai, licença MIT,
© 2018 DataSnaek): lá, a IA de batalha naval sorteia muitas posições possíveis para os navios
restantes, descarta as que contradizem os tiros na água, soma tudo num mapa de frequências e ataca
a casa mais provável. Aqui, cada unidade do jogador que sumiu é
sorteada a partir da última posição vista e da distância que pode ter andado; as células que o radar
vê sem encontrá-la fazem o papel dos tiros na água.

Com o alvo à vista, a IA concentra o fogo na unidade mais fácil de destruir, só usa armas que funcionam
contra ela e, quando tem alcance maior, recua para fora do alcance do alvo.
"""

import math
import random
from typing import Dict, List, Optional, Tuple

DIVE_DEPTH = 40


class EnemyAI:
    def __init__(self, team_name: str, samples: int = 300, seed: Optional[int] = None):
        self.team_name = team_name
        self.samples = samples
        self.rng = random.Random(seed)
        self.turn = 0
        self.last_seen: Dict[str, Tuple[float, float, int]] = {}
        self.heatmap: List[List[float]] = []

    def compute_turn(self, interpreter, player_units: list):
        """Gera as ações do turno para o time controlado pela IA"""
        self.turn += 1
        self.heatmap = []
        renderer = interpreter.renderer
        own = [u for u in self._members(interpreter, interpreter.teams.get(self.team_name, [])) if u.is_alive()]
        enemies = [u for u in self._members(interpreter, player_units) if u.is_alive()]
        if not own or not enemies:
            return

        visible = self._observe(renderer, interpreter, own, enemies)
        if not visible:
            self.heatmap = self._build_heatmap(renderer, interpreter, own, enemies)
            self._sonar_best(interpreter, own)
            visible = self._observe(renderer, interpreter, own, enemies)

        for unit in sorted(own, key=lambda u: not self._has_shot(u, visible)):
            if not unit.is_alive():
                continue
            visible = self._observe(renderer, interpreter, own, enemies)
            if visible:
                self._engage(interpreter, unit, visible)
            else:
                if not self.heatmap:
                    self.heatmap = self._build_heatmap(renderer, interpreter, own, enemies)
                self._hunt(interpreter, unit)
            self._hide_if_submarine(interpreter, unit)

        if not self._observe(renderer, interpreter, own, enemies):
            self.heatmap = self._build_heatmap(renderer, interpreter, own, enemies)
            self._sonar_best(interpreter, own)

    # ---------- percepção ----------

    @staticmethod
    def _members(interpreter, names) -> list:
        return [interpreter.units[name] for name in names if name in interpreter.units]

    def _observe(self, renderer, interpreter, own, enemies) -> list:
        if renderer is None:
            visible = enemies
        else:
            cells = renderer.visible_cells(interpreter.units, [u.name for u in own if u.is_alive()])
            visible = [e for e in enemies if e.is_alive() and renderer.is_shown(e, False, cells)]
        for enemy in visible:
            self.last_seen[enemy.name] = (enemy.x, enemy.y, self.turn)
        return visible

    def _build_heatmap(self, renderer, interpreter, own, enemies) -> List[List[float]]:
        """Mapa de calor por Monte Carlo: probabilidade de cada célula esconder uma unidade do jogador."""
        width, height = (renderer.width, renderer.height) if renderer else (20, 10)
        heat = [[0.0] * width for _ in range(height)]
        seen = renderer.visible_cells(interpreter.units, [u.name for u in own]) if renderer else set()
        # sem nenhuma pista, supõe que o inimigo começou do outro lado do mapa
        far_side = width * 10 - sum(u.x for u in own) / len(own)

        for enemy in enemies:
            memory = self.last_seen.get(enemy.name)
            samples = []
            for _ in range(self.samples * 4):
                if len(samples) >= self.samples:
                    break
                if memory:
                    x0, y0, seen_turn = memory
                    reach = enemy.speed * max(1, self.turn - seen_turn)
                    angle = self.rng.uniform(0, 2 * math.pi)
                    distance = reach * math.sqrt(self.rng.random())
                    x, y = x0 + math.cos(angle) * distance, y0 + math.sin(angle) * distance
                else:
                    x, y = self.rng.triangular(0, width * 10, far_side), self.rng.uniform(0, height * 10)
                if not (0 <= x < width * 10 and 0 <= y < height * 10):
                    continue
                cell = (int(x // 10), int(y // 10))
                if renderer and enemy.kind != "aircraft" and renderer.terrain[cell[1]][cell[0]].strip() == "I":
                    continue
                weight = 1.0
                if cell in seen:
                    # o radar olhou e não viu: só um submarino submerso poderia estar ali
                    if enemy.kind != "submarine":
                        continue
                    weight = 0.25
                samples.append((cell, weight))

            total = sum(weight for _, weight in samples)
            for (gx, gy), weight in samples:
                heat[gy][gx] += weight / total
        return heat

    def _hottest_cell(self, unit) -> Optional[Tuple[float, float]]:
        """Destino que deixa mais probabilidade dentro do raio de visão da unidade."""
        reach = max(1, unit.radar_range // 10)
        height, width = len(self.heatmap), len(self.heatmap[0])
        best, best_score = None, 0.0
        for gy in range(height):
            for gx in range(width):
                mass = sum(
                    self.heatmap[y][x]
                    for y in range(max(0, gy - reach), min(height, gy + reach + 1))
                    for x in range(max(0, gx - reach), min(width, gx + reach + 1))
                )
                if mass <= 0:
                    continue
                cx, cy = gx * 10 + 5, gy * 10 + 5
                score = mass / (1 + math.hypot(cx - unit.x, cy - unit.y) / (unit.speed * 6))
                if score > best_score:
                    best, best_score = (cx, cy), score
        return best

    def _sonar_best(self, interpreter, own) -> None:
        if not self.heatmap:
            return
        best, best_mass = None, 0.0
        for unit in own:
            if not unit.is_alive() or unit.sonar_cooldown > 0:
                continue
            reach = unit.sonar_range // 10
            ux, uy = int(unit.x // 10), int(unit.y // 10)
            mass = sum(
                value
                for gy, row in enumerate(self.heatmap)
                for gx, value in enumerate(row)
                if value and max(abs(gx - ux), abs(gy - uy)) <= reach
            )
            if mass > best_mass:
                best, best_mass = unit, mass
        # o pulso denuncia a posição, então só vale quando cobre boa parte do mapa de calor
        if best is not None and best_mass >= 0.35:
            interpreter.execute_statement({"type": "SonarStatement", "unit": best.name})

    # ---------- combate ----------

    @staticmethod
    def _can_hurt(weapon, target) -> bool:
        if target.kind == "submarine" and target.depth > 0 and weapon["kind"] != "torpedo":
            return False
        if target.kind == "aircraft" and weapon["kind"] == "torpedo":
            return False
        return True

    @staticmethod
    def _ready(weapon) -> bool:
        return weapon["cooldown"] == 0 and weapon["ammo"] > 0

    def _expected_damage(self, interpreter, weapon, target) -> float:
        damage = max(1, weapon["properties"]["damage"] - target.armor)
        renderer = interpreter.renderer
        if renderer and target.kind != "aircraft" and renderer.get_terrain_at(target.x, target.y) == "#":
            damage = max(1, int(damage * 0.5))
        return damage * (2 if target.exposed else 1)

    def _has_shot(self, unit, visible) -> bool:
        return any(self._ready(w) and self._can_hurt(w, t) for w in unit.weapons for t in visible)

    def _best_shot(self, interpreter, unit, visible):
        budget = min(unit.movement_left, unit.speed)
        best, best_score = None, -1.0
        for target in visible:
            distance = math.hypot(target.x - unit.x, target.y - unit.y)
            for weapon in unit.weapons:
                weapon_range = weapon["properties"]["range"]
                if not (self._ready(weapon) and self._can_hurt(weapon, target)) or distance - budget > weapon_range:
                    continue
                damage = self._expected_damage(interpreter, weapon, target)
                score = 1000 - target.hp if damage >= target.hp else damage / target.hp
                if distance <= weapon_range:
                    score += 0.01
                if score > best_score:
                    best, best_score = (weapon, target), score
        return best

    def _engage(self, interpreter, unit, visible) -> None:
        for _ in range(len(unit.weapons)):
            shot = self._best_shot(interpreter, unit, [t for t in visible if t.is_alive()])
            if shot is None:
                break
            weapon, target = shot
            weapon_range = weapon["properties"]["range"]
            if math.hypot(target.x - unit.x, target.y - unit.y) > weapon_range:
                self._move_towards(interpreter, unit, target.x, target.y, stop_at=weapon_range * 0.9)
                if math.hypot(target.x - unit.x, target.y - unit.y) > weapon_range:
                    break
            interpreter.execute_statement({
                "type": "FireStatement",
                "attacker": unit.name,
                "weapon": weapon["name"],
                "target": target.name,
            })

        alive = [t for t in visible if t.is_alive()]
        if not alive:
            return
        threats = [t for t in alive if self._threat_range(t, unit) >= math.hypot(t.x - unit.x, t.y - unit.y)]
        my_range = max((w["properties"]["range"] for w in unit.weapons if w["ammo"] > 0), default=0)
        if threats:
            # com alcance maior, recua para fora do alcance do alvo sem sair do próprio alcance
            threat = min(threats, key=lambda t: math.hypot(t.x - unit.x, t.y - unit.y))
            if my_range > self._threat_range(threat, unit):
                self._move_away(interpreter, unit, threat, self._threat_range(threat, unit) + 5)
                return
        if my_range == 0:
            nearest = min(alive, key=lambda t: math.hypot(t.x - unit.x, t.y - unit.y))
            self._move_away(interpreter, unit, nearest, nearest.radar_range + 5)
        else:
            target = min(alive, key=lambda t: t.hp)
            self._move_towards(interpreter, unit, target.x, target.y, stop_at=max(my_range * 0.9, 10))

    def _threat_range(self, enemy, unit) -> float:
        return max(
            (w["properties"]["range"] for w in enemy.weapons if w["ammo"] > 0 and self._can_hurt(w, unit)),
            default=0,
        )

    def _hunt(self, interpreter, unit) -> None:
        destination = self._hottest_cell(unit)
        if destination is None:
            return
        self._move_towards(interpreter, unit, *destination)

    def _hide_if_submarine(self, interpreter, unit) -> None:
        if unit.kind != "submarine" or not unit.is_alive() or unit.depth > 0 or unit.must_surface_next_turn:
            return
        renderer = interpreter.renderer
        if renderer and renderer.get_terrain_at(unit.x, unit.y) == "~":
            return
        interpreter.execute_statement({"type": "DiveStatement", "unit": unit.name, "depth": DIVE_DEPTH})

    # ---------- movimento ----------

    def _move_towards(self, interpreter, unit, tx: float, ty: float, stop_at: float = 0) -> None:
        distance = math.hypot(tx - unit.x, ty - unit.y)
        step = min(unit.movement_left, unit.speed, distance - stop_at)
        if step < 1:
            return
        self._step(interpreter, unit, math.atan2(ty - unit.y, tx - unit.x), step)

    def _move_away(self, interpreter, unit, threat, safe_distance: float) -> None:
        distance = math.hypot(unit.x - threat.x, unit.y - threat.y)
        step = min(unit.movement_left, unit.speed, safe_distance - distance)
        if step < 1:
            return
        self._step(interpreter, unit, math.atan2(unit.y - threat.y, unit.x - threat.x), step)

    def _step(self, interpreter, unit, angle: float, step: float) -> None:
        renderer = interpreter.renderer
        width, height = (renderer.width * 10, renderer.height * 10) if renderer else (200, 100)
        for offset in (0, 0.4, -0.4, 0.8, -0.8, 1.2, -1.2):
            x = round(min(max(unit.x + math.cos(angle + offset) * step, 0), width - 1))
            y = round(min(max(unit.y + math.sin(angle + offset) * step, 0), height - 1))
            if (x, y) == (round(unit.x), round(unit.y)):
                continue
            if renderer and unit.kind != "aircraft" and renderer.get_terrain_at(x, y) == "I":
                continue
            interpreter.execute_statement({"type": "MoveStatement", "unit": unit.name, "x": x, "y": y})
            return
