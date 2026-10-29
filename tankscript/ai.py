import math
from typing import Dict, Any

class EnemyAI:
    def __init__(self, team_name: str):
        self.team_name = team_name

    def compute_turn(self, interpreter, player_units: list):
        """Gera ações automáticas para o time controlado pela IA"""
        enemy_members = interpreter.teams.get(self.team_name, [])
        
        for name in enemy_members:
            unit = interpreter.units.get(name)
            if not unit or not unit.is_alive():
                continue

            # Encontra alvo do jogador mais próximo
            target = self._get_closest_target(unit, interpreter, player_units)
            if not target:
                continue

            dist = math.sqrt((target.x - unit.x)**2 + (target.y - unit.y)**2)
            
            # Se tiver arma disponível, tenta atirar
            ready_weapon = next((w for w in unit.weapons if w["cooldown"] == 0 and w["ammo"] > 0), None)

            if ready_weapon and dist <= ready_weapon["properties"].get("range", 0):
                interpreter.execute_statement({
                    "type": "FireStatement",
                    "attacker": unit.name,
                    "weapon": ready_weapon["name"],
                    "target": target.name
                })
            else:
                # Aproxima-se do alvo até ficar no alcance da melhor arma, andando no máximo `speed`
                best_range = max((w["properties"]["range"] for w in unit.weapons), default=0)
                step = min(unit.speed, max(0, dist - best_range * 0.8))
                if dist == 0 or step == 0:
                    continue

                interpreter.execute_statement({
                    "type": "MoveStatement",
                    "unit": unit.name,
                    "x": max(0, min(190, round(unit.x + (target.x - unit.x) / dist * step))),
                    "y": max(0, min(90, round(unit.y + (target.y - unit.y) / dist * step)))
                })

    def _get_closest_target(self, unit, interpreter, player_units):
        closest = None
        min_dist = float("inf")
        for p_name in player_units:
            p_unit = interpreter.units.get(p_name)
            if p_unit and p_unit.is_alive():
                dist = math.sqrt((p_unit.x - unit.x)**2 + (p_unit.y - unit.y)**2)
                if dist < min_dist:
                    min_dist = dist
                    closest = p_unit
        return closest