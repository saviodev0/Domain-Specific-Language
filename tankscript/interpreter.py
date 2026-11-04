import math
from typing import Dict, List, Any
from .catalogo import ARMAS, RECARGA_DO_SONAR, UNIDADES
from .renderer import GridRenderer

class Unit:
    def __init__(self, name: str, kind: str, weapons: List[Dict]):
        stats = UNIDADES[kind]
        self.name = name
        self.kind = kind
        self.hp = stats["hp"]
        self.max_hp = self.hp
        self.armor = stats["armor"]
        self.speed = stats["speed"]
        self.radar_range = stats["radar"]
        self.sonar_range = stats["sonar"]
        self.sonar_cooldown = 0
        self.depth = 0
        self.x: int | float = 0
        self.y: int | float = 0
        # Antes do primeiro turno o posicionamento é livre; depois, cada turno libera `speed`.
        self.movement_left = math.inf

        # armas com ammo e cooldown; os atributos vêm do tipo da arma
        self.weapons = []
        for w in weapons:
            w_copy = dict(w)
            w_copy["properties"] = dict(ARMAS[w["kind"]])
            w_copy["ammo"] = w_copy["properties"]["ammo"]
            w_copy["cooldown"] = 0
            w_copy["max_cooldown"] = w_copy["properties"]["cooldown"]
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
    UNIT_KINDS = {
        "TankDeclaration": "tank",
        "SubmarineDeclaration": "submarine",
        "AircraftDeclaration": "aircraft",
    }

    def __init__(self, ast: Dict[str, Any], renderer: GridRenderer = None):
        self.ast = ast
        self.units: Dict[str, Unit] = {}
        self.teams: Dict[str, List[str]] = {}
        self.battles: List[Dict[str, str]] = []
        self.renderer = renderer

    def execute_declaration(self, decl: Dict[str, Any]):
        dtype = decl["type"]
        if dtype in self.UNIT_KINDS:
            unit = Unit(decl["name"], self.UNIT_KINDS[dtype], decl["weapons"])
            self.units[unit.name] = unit

        elif dtype == "TeamDeclaration":
            self.teams[decl["name"]] = decl["members"]

        elif dtype == "BattleDeclaration":
            self.battles.append({"name": decl["name"], "team1": decl["team1"], "team2": decl["team2"]})

    def tick_cooldowns_and_effects(self):
        """Reduz cooldowns e expiração de sonar no início do turno"""
        for unit in self.units.values():
            unit.movement_left = unit.speed
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
            if unit.sonar_cooldown > 0:
                unit.sonar_cooldown -= 1

            for w in unit.weapons:
                if w["cooldown"] > 0:
                    w["cooldown"] -= 1

    def execute_statement(self, stmt: Dict[str, Any]):
        stype = stmt["type"]

        if stype == "MoveStatement":
            unit = self.units.get(stmt["unit"])
            if unit and unit.is_alive():
                x, y = stmt["x"], stmt["y"]
                dist = math.hypot(x - unit.x, y - unit.y)
                if dist > unit.movement_left + 0.5:
                    if unit.movement_left <= 0:
                        print(f"[SEM MOVIMENTO] {unit.name} já andou {unit.speed} neste turno")
                        return
                    ratio = unit.movement_left / dist
                    x = round(unit.x + (x - unit.x) * ratio)
                    y = round(unit.y + (y - unit.y) * ratio)
                    print(f"[MOVE LIMITADO] {unit.name} anda até {unit.speed} por turno e parou em ({x}, {y})")

                # Regra de Terreno: Ilha ("I") bloqueia o caminho, exceto de aeronaves. No posicionamento
                # inicial, antes do primeiro turno, a unidade só não pode começar em cima da ilha.
                if self.renderer and unit.kind != "aircraft":
                    if math.isinf(unit.movement_left):
                        stop = (round(unit.x), round(unit.y)) if self.renderer.get_terrain_at(x, y) == "I" else None
                    else:
                        stop = self._last_point_before_island(unit.x, unit.y, x, y)
                    if stop is not None:
                        if stop == (round(unit.x), round(unit.y)):
                            print(f"[COLISÃO] {unit.name} tentou mover para uma Ilha/Montanha e foi bloqueado!")
                            return
                        x, y = stop
                        print(f"[COLISÃO] {unit.name} encontrou uma Ilha/Montanha no caminho e parou em ({x}, {y})")

                unit.movement_left = max(0, unit.movement_left - math.hypot(x - unit.x, y - unit.y))
                unit.x = x
                unit.y = y
                print(f"[MOVE] {unit.name} moveu para ({unit.x}, {unit.y})")

        elif stype == "DiveStatement":
            unit = self.units.get(stmt["unit"])
            if unit and unit.is_alive() and unit.kind == "submarine":
                if self.renderer and self.renderer.get_terrain_at(unit.x, unit.y) == "~":
                    print(f"[DIVE IMPOSSÍVEL] {unit.name} está em Água Rasa (~) e não pode submergir!")
                elif unit.must_surface_next_turn:
                    print(f"[DIVE BLOQUEADO] {unit.name} atacou submerso no último turno e precisa emergir!")
                elif unit.exposed:
                    print(f"[DIVE BLOQUEADO] {unit.name} está EXPOSTO e só pode submergir no próximo turno!")
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
                if unit.sonar_cooldown > 0:
                    print(f"[SONAR RECARREGANDO] {unit.name} só pode usar o sonar de novo em {unit.sonar_cooldown} turno(s)")
                    return
                print(f"📡 [SONAR ATIVADO] {unit.name} emitiu um pulso de radar/sonar!")
                unit.sonar_cooldown = RECARGA_DO_SONAR
                # o pulso denuncia quem o emitiu até o próximo turno
                unit.sonar_ping_turns = max(unit.sonar_ping_turns, 1)
                print(f"   -> [RUÍDO] O pulso revelou a posição de {unit.name} ao inimigo!")
                reach = unit.sonar_range // 10
                ux, uy = self._cell(unit)
                for target in self.units.values():
                    if target.name == unit.name or not target.is_alive() or self._same_team(unit, target):
                        continue
                    tx, ty = self._cell(target)
                    if max(abs(tx - ux), abs(ty - uy)) <= reach:
                        target.sonar_ping_turns = 2
                        print(f"   -> [PING] Unidade detectada: {target.name} na posição ({target.x}, {target.y})!")

        elif stype == "FireStatement":
            self.handle_fire(stmt["attacker"], stmt["weapon"], stmt["target"])

        elif stype == "AttackStatement":
            attacker = self.units.get(stmt["attacker"])
            if attacker and attacker.weapons:
                ready = next((w for w in attacker.weapons if w["cooldown"] == 0 and w["ammo"] > 0), attacker.weapons[0])
                self.handle_fire(stmt["attacker"], ready["name"], stmt["target"])

        elif stype == "IfStatement":
            if self.evaluate_expression(stmt["condition"]):
                for inner in stmt["body"]:
                    self.execute_statement(inner)

        elif stype == "RepeatStatement":
            for _ in range(stmt["count"]):
                for inner in stmt["body"]:
                    self.execute_statement(inner)

    def _last_point_before_island(self, x0, y0, x1, y1):
        """Percorre o caminho e devolve o último ponto livre antes da primeira ilha, ou None se não houver ilha."""
        steps = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0)))
        previous = (round(x0), round(y0))
        for step in range(1, steps + 1):
            point = (round(x0 + (x1 - x0) * step / steps), round(y0 + (y1 - y0) * step / steps))
            if self.renderer.get_terrain_at(*point) == "I":
                return previous
            previous = point
        return None

    def _cell(self, unit: Unit) -> tuple:
        if self.renderer:
            return self.renderer.cell_of(unit.x, unit.y)
        return int(unit.x // 10), int(unit.y // 10)

    def _team_of(self, name: str):
        return next((team for team, members in self.teams.items() if name in members), None)

    def _same_team(self, a: Unit, b: Unit) -> bool:
        team = self._team_of(a.name)
        return team is not None and team == self._team_of(b.name)

    def _can_see(self, observer: Unit, target: Unit) -> bool:
        """Uma unidade só mira no que alguém da sua equipe enxerga: radar, sonar ou alvo exposto."""
        team = self._team_of(observer.name)
        if self.renderer is None or team is None or self._same_team(observer, target):
            return True
        cells = self.renderer.visible_cells(self.units, self.teams[team])
        return self.renderer.is_shown(target, False, cells)

    def handle_fire(self, attacker_name: str, weapon_name: str, target_name: str):
        attacker = self.units.get(attacker_name)
        target = self.units.get(target_name)

        if not attacker or not attacker.is_alive() or not target or not target.is_alive():
            print("[FIRE FALHOU] Unidade inválida ou destruída.")
            return

        if attacker is target or self._same_team(attacker, target):
            print(f"[FIRE FALHOU] {attacker.name} não atira na própria equipe!")
            return

        if not self._can_see(attacker, target):
            print(f"[SEM VISÃO] {attacker.name} não enxerga {target.name}; aproxime-se ou use o sonar")
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

        if target.kind == "submarine" and target.depth > 0 and weapon["kind"] != "torpedo":
            print("[FIRE INEFICAZ] Só torpedos atingem submarinos submersos!")
            return
        if target.kind == "aircraft" and weapon["kind"] == "torpedo":
            print("[FIRE INEFICAZ] Torpedos não atingem aeronaves!")
            return

        # Consome Munição e aplica Cooldown
        weapon["ammo"] -= 1
        weapon["cooldown"] = weapon["max_cooldown"]

        # Modificador de Terreno (# Ruínas/Cobertura reduz dano em 50%)
        defense_mult = 1.0
        if self.renderer and target.kind != "aircraft" and self.renderer.get_terrain_at(target.x, target.y) == "#":
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

    def evaluate_value(self, node: Dict[str, Any]) -> int | float | str:
        if node["type"] == "Literal": return node["value"]
        if node["type"] == "MemberAccess":
            unit = self.units.get(node["unit"])
            attribute = "radar_range" if node["property"] == "radar" else node["property"]
            if unit: return getattr(unit, attribute, 0)
        return 0