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

    def get_terrain_at(self, x: int, y: int) -> str:
        gx = min(max(0, x // 10), self.width - 1)
        gy = min(max(0, y // 10), self.height - 1)
        return self.terrain[gy][gx].strip()

    def draw(self, units: dict, player_team_members: list):
        self.clear_screen()
        grid = [row[:] for row in self.terrain]

        visible_cells = set()
        for name in player_team_members:
            u = units.get(name)
            if u and u.is_alive():
                gx = min(max(0, u.x // 10), self.width - 1)
                gy = min(max(0, u.y // 10), self.height - 1)
                radar = getattr(u, 'radar_range', 60) // 10
                for dy in range(-radar, radar + 1):
                    for dx in range(-radar, radar + 1):
                        nx, ny = gx + dx, gy + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            visible_cells.add((nx, ny))

        for name, unit in units.items():
            if not unit.is_alive():
                continue

            gx = min(max(0, unit.x // 10), self.width - 1)
            gy = min(max(0, unit.y // 10), self.height - 1)
            is_player_unit = name in player_team_members
            is_visible = (gx, gy) in visible_cells or getattr(unit, 'sonar_ping_turns', 0) > 0

            if is_player_unit or is_visible:
                if unit.kind == "tank":
                    color = "\033[92m" if is_player_unit else "\033[91m"
                    icon = f"{color} T \033[0m"
                elif unit.kind == "submarine":
                    if unit.depth > 0 and not is_player_unit and not getattr(unit, 'exposed', False) and getattr(unit, 'sonar_ping_turns', 0) == 0:
                        continue
                    color = "\033[96m" if is_player_unit else "\033[93m"
                    icon = f"{color}~S~\033[0m" if unit.depth > 0 else f"{color} S \033[0m"

                grid[gy][gx] = icon

        print("=" * (self.width * 3 + 4))
        print("           ARENA TANKIO — FOG OF WAR & TERRAIN")
        print(" Legenda: [T] Tanque | [S] Submarino | [I] Ilha | [#] Cobertura | [?] Névoa")
        print("=" * (self.width * 3 + 4))

        for y in range(self.height):
            row_str = "|"
            for x in range(self.width):
                if (x, y) in visible_cells:
                    row_str += grid[y][x]
                else:
                    row_str += " ? "
            row_str += "|"
            print(row_str)

        print("=" * (self.width * 3 + 4))