import os

class GridRenderer:
    def __init__(self, width: int = 20, height: int = 10):
        self.width = width
        self.height = height
        self.terrain = [[" . " for _ in range(self.width)] for _ in range(self.height)]
        self._build_terrain()

    def _build_terrain(self):
        self.terrain[2][8] = " I "
        self.terrain[3][8] = " I "
        self.terrain[5][5] = " # "
        self.terrain[6][5] = " # "
        self.terrain[1][12] = " ~ "
        self.terrain[2][12] = " ~ "

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def cell_of(self, x: int | float, y: int | float) -> tuple[int, int]:
        gx = int(min(max(0, x // 10), self.width - 1))
        gy = int(min(max(0, y // 10), self.height - 1))
        return gx, gy

    def get_terrain_at(self, x: int | float, y: int | float) -> str:
        gx, gy = self.cell_of(x, y)
        return self.terrain[gy][gx].strip()

    def visible_cells(self, units: dict, player_team_members: list) -> set:
        visible_cells = set()
        for name in player_team_members:
            u = units.get(name)
            if u and u.is_alive():
                gx, gy = self.cell_of(u.x, u.y)
                radar = int(getattr(u, 'radar_range', 60) // 10)
                for dy in range(-radar, radar + 1):
                    for dx in range(-radar, radar + 1):
                        nx, ny = gx + dx, gy + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            visible_cells.add((nx, ny))
        return visible_cells

    def is_shown(self, unit, is_player_unit: bool, visible_cells: set) -> bool:
        if not unit.is_alive():
            return False
        if is_player_unit:
            return True
        pinged = getattr(unit, 'sonar_ping_turns', 0) > 0
        if unit.kind == "submarine" and unit.depth > 0 and not getattr(unit, 'exposed', False) and not pinged:
            return False
        return self.cell_of(unit.x, unit.y) in visible_cells or pinged

    def draw(self, units: dict, player_team_members: list):
        self.clear_screen()
        grid = [row[:] for row in self.terrain]
        visible_cells = self.visible_cells(units, player_team_members)
        revealed = set()

        for name, unit in units.items():
            is_player_unit = name in player_team_members
            if not self.is_shown(unit, is_player_unit, visible_cells):
                continue

            gx, gy = self.cell_of(unit.x, unit.y)
            if unit.kind == "tank":
                color = "\033[92m" if is_player_unit else "\033[91m"
                icon = f"{color} T \033[0m"
            elif unit.kind == "aircraft":
                color = "\033[92m" if is_player_unit else "\033[91m"
                icon = f"{color} A \033[0m"
            else:
                color = "\033[96m" if is_player_unit else "\033[93m"
                icon = f"{color}~S~\033[0m" if unit.depth > 0 else f"{color} S \033[0m"

            grid[gy][gx] = icon
            revealed.add((gx, gy))

        print("=" * (self.width * 3 + 4))
        print("           ARENA TANKIO — FOG OF WAR & TERRAIN")
        print(" Legenda: [T] Tanque | [S] Submarino | [A] Aeronave | [I] Ilha | [#] Cobertura | [?] Névoa")
        print("=" * (self.width * 3 + 4))

        for y in range(self.height):
            row_str = "|"
            for x in range(self.width):
                if (x, y) in visible_cells or (x, y) in revealed:
                    row_str += grid[y][x]
                else:
                    row_str += " ? "
            row_str += "|"
            print(row_str)

        print("=" * (self.width * 3 + 4))
