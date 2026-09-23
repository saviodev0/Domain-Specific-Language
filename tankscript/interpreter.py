import math
from typing import Dict, List, Any
from .renderer import GridRenderer

class Unit:
    def __init__(self, name: str, kind: str, properties: Dict[str, int], weapons: List[Dict]):
        self.name = name
        self.kind = kind
        self.hp = properties.get("hp", 100)
        self.max_hp = self.hp
        self.armor = properties.get("armor", 0)
        self.speed = properties.get("speed", 10)
        self.radar_range = properties.get("radar", 60)
        self.depth = properties.get("depth", 0) if kind == "submarine" else 0
        self.x = 0
        self.y = 0

        # armas com ammo e cooldown
        self.weapons = []
        for w in weapons:
            w_copy = dict(w)
            w_copy["ammo"] = w["properties"].get("ammo", 5)
            w_copy["cooldown"] = 0
            w_copy["max_cooldown"] = w["properties"].get("cooldown", 1)
            self.weapons.append(w_copy)

        self.exposed = False
        self.must_surface_next_turn = False
        self.sonar_ping_turns = 0

    def is_alive(self) -> bool:
        return self.hp > 0

    def __repr__(self):
        exposed_tag = " [EXPOSTO! 2X DANO]" if self.exposed else ""
        sonar_tag = " [DETECTADO VIA SONAR]" if self.sonar_ping_turns > 0 else ""
        return f"[{self.kind.upper()}] {self.name} | HP: {self.hp}/{self.max_hp} | Pos: ({self.x}, {self.y}) | Prof: {self.depth}m{exposed_tag}{sonar_tag}"


class Interpreter:
    def __init__(self, ast: Dict[str, Any], renderer: GridRenderer = None):
        self.ast = ast
        self.units: Dict[str, Unit] = {}
        self.teams: Dict[str, List[str]] = {}
        self.battles: List[Dict[str, str]] = []
        self.renderer = renderer

    def execute_declaration(self, decl: Dict[str, Any]):
        dtype = decl["type"]
        if dtype in ("TankDeclaration", "SubmarineDeclaration"):
            kind = "tank" if dtype == "TankDeclaration" else "submarine"
            unit = Unit(decl["name"], kind, decl["properties"], decl["weapons"])
            self.units[unit.name] = unit

        elif dtype == "TeamDeclaration":
            self.teams[decl["name"]] = decl["members"]

        elif dtype == "BattleDeclaration":
            self.battles.append({"name": decl["name"], "team1": decl["team1"], "team2": decl["team2"]})

    def tick_cooldowns_and_effects(self):
        """Reduz cooldowns e expiração de sonar no início do turno"""
        for unit in self.units.values():
            if unit.kind == "submarine":
                if unit.must_surface_next_turn:
                    unit.depth = 0
                    unit.exposed = True
                    unit.must_surface_next_turn = False
                    print(f"⚠️  [EXPOSIÇÃO] {unit.name} foi forçado a subir e está EXPOSTO (Dano 2x)!")
                elif unit.exposed:
                    unit.exposed = False

            if unit.sonar_ping_turns > 0:
                unit.sonar_ping_turns -= 1

            for w in unit.weapons:
                if w["cooldown"] > 0:
                    w["cooldown"] -= 1

    def execute_statement(self, stmt: Dict[str, Any]):
        stype = stmt["type"]

        if stype == "MoveStatement":
            unit = self.units.get(stmt["unit"])
            if unit and unit.is_alive():
                # Regra de Terreno: Ilha ("I") bloqueia movimento
                if self.renderer:
                    terrain = self.renderer.get_terrain_at(stmt["x"], stmt["y"])
                    if terrain == "I":
                        print(f"[COLISÃO] {unit.name} tentou mover para uma Ilha/Montanha e foi bloqueado!")
                        return

                unit.x = stmt["x"]
                unit.y = stmt["y"]
                print(f"[MOVE] {unit.name} moveu para ({unit.x}, {unit.y})")

        elif stype == "DiveStatement":
            unit = self.units.get(stmt["unit"])
            if unit and unit.is_alive() and unit.kind == "submarine":
                if self.renderer and self.renderer.get_terrain_at(unit.x, unit.y) == "~":
                    print(f"[DIVE IMPOSSÍVEL] {unit.name} está em Água Rasa (~) e não pode submergir!")
                elif unit.must_surface_next_turn:
                    print(f"[DIVE BLOQUEADO] {unit.name} atacou submerso no último turno e precisa emergir!")
                else:
                    unit.depth = stmt["depth"]
                    print(f"[DIVE] {unit.name} submergiu para {unit.depth}m")

        elif stype == "SurfaceStatement":
            unit = self.units.get(stmt["unit"])
            if unit and unit.is_alive() and unit.kind == "submarine":
                unit.depth = 0
                print(f"[SURFACE] {unit.name} emergiu")

        elif stype == "SonarStatement":
            unit = self.units.get(stmt["unit"])
            if unit and unit.is_alive():
                print(f"📡 [SONAR ATIVADO] {unit.name} emitiu um pulso de radar/sonar!")
                for target in self.units.values():
                    if target.name != unit.name and target.is_alive():
                        dist = math.sqrt((target.x - unit.x)**2 + (target.y - unit.y)**2)
                        if dist <= unit.radar_range * 1.5:
                            target.sonar_ping_turns = 2
                            print(f"   -> [PING] Unidade detectada: {target.name} na posição ({target.x}, {target.y})!")

        elif stype == "FireStatement":
            self.handle_fire(stmt["attacker"], stmt["weapon"], stmt["target"])

        elif stype == "AttackStatement":
            attacker = self.units.get(stmt["attacker"])
            if attacker and attacker.weapons:
                self.handle_fire(stmt["attacker"], attacker.weapons[0]["name"], stmt["target"])

        elif stype == "IfStatement":
            if self.evaluate_expression(stmt["condition"]):
                for inner in stmt["body"]:
                    self.execute_statement(inner)

        elif stype == "RepeatStatement":
            for _ in range(stmt["count"]):
                for inner in stmt["body"]:
                    self.execute_statement(inner)

    def handle_fire(self, attacker_name: str, weapon_name: str, target_name: str):
        attacker = self.units.get(attacker_name)
        target = self.units.get(target_name)

        if not attacker or not attacker.is_alive() or not target or not target.is_alive():
            print("[FIRE FALHOU] Unidade inválida ou destruída.")
            return

        weapon = next((w for w in attacker.weapons if w["name"] == weapon_name), None)
        if not weapon:
            print(f"[FIRE FALHOU] {attacker.name} não possui a arma '{weapon_name}'")
            return

        # Validação de Cooldown e Munição
        if weapon["cooldown"] > 0:
            print(f"[RECARREGANDO] {weapon['name']} em cooldown por mais {weapon['cooldown']} turno(s)!")
            return
        if weapon["ammo"] <= 0:
            print(f"[SEM MUNIÇÃO] {weapon['name']} está sem munição disponível!")
            return

        dist = math.sqrt((target.x - attacker.x)**2 + (target.y - attacker.y)**2)
        if dist > weapon["properties"].get("range", 0):
            print(f"[FIRE ERROU] {target.name} fora do alcance!")
            return

        if target.kind == "submarine" and target.depth > 0 and weapon["kind"] == "gun":
            print(f"[FIRE INEFICAZ] Canhões não atingem submarinos submersos!")
            return

        # Consome Munição e aplica Cooldown
        weapon["ammo"] -= 1
        weapon["cooldown"] = weapon["max_cooldown"]

        # Modificador de Terreno (# Ruínas/Cobertura reduz dano em 50%)
        defense_mult = 1.0
        if self.renderer and self.renderer.get_terrain_at(target.x, target.y) == "#":
            defense_mult = 0.5
            print(f"🛡️  [COBERTURA] {target.name} está em Ruínas/Cobertura (#) e reduz o dano em 50%!")

        base_damage = weapon["properties"].get("damage", 0)
        effective_damage = max(1, int((base_damage - target.armor) * defense_mult))

        if target.exposed:
            effective_damage *= 2
            print(f"💥 [CRÍTICO] {target.name} está EXPOSTO! Dano 2x!")

        target.hp = max(0, target.hp - effective_damage)
        print(f"[FIRE SUCESSO] {attacker.name} usou {weapon['name']} em {target.name}! Dano: {effective_damage} (HP: {target.hp}) [Munição: {weapon['ammo']}]")

        if attacker.kind == "submarine" and attacker.depth > 0:
            attacker.must_surface_next_turn = True
            print(f"⚠️  [ALERTA] {attacker.name} atirou submerso e subirá exposto no próximo turno!")

    def evaluate_expression(self, expr: Dict[str, Any]) -> bool:
        if expr["type"] == "BinaryExpression":
            left = self.evaluate_value(expr["left"])
            right = self.evaluate_value(expr["right"])
            op = expr["operator"]
            if op == "<": return left < right
            if op == ">": return left > right
            if op == "==": return left == right
        return False

    def evaluate_value(self, node: Dict[str, Any]) -> int:
        if node["type"] == "Literal": return node["value"]
        if node["type"] == "MemberAccess":
            unit = self.units.get(node["unit"])
            if unit: return getattr(unit, node["property"], 0)
        return 0