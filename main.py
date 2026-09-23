import sys
from tankscript import Lexer, Parser, Interpreter, GridRenderer, EnemyAI

def main():
    renderer = GridRenderer(width=20, height=10)
    script_path = "scripts/battle.tank"

    try:
        with open(script_path, "r", encoding="utf-8") as file:
            code = file.read()
    except FileNotFoundError:
        print(f"Erro: Arquivo '{script_path}' não encontrado.")
        sys.exit(1)

    # 1. Parsing
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    interpreter = Interpreter(ast, renderer=renderer)

    for decl in interpreter.ast["declarations"]:
        interpreter.execute_declaration(decl)

    # Executa scripts do arquivo base
    for stmt in interpreter.ast["statements"]:
        interpreter.execute_statement(stmt)

    player_team = interpreter.teams.get("Blue", [])
    ai_engine = EnemyAI(team_name="Red")

    turn = 1
    while True:
        interpreter.tick_cooldowns_and_effects()
        renderer.draw(interpreter.units, player_team)

        print(f"\n--- TURNO {turn} ---")
        print("Status do Esquadrão Jogador (Blue):")
        for u_name in player_team:
            u = interpreter.units.get(u_name)
            if u:
                print(f"  > {u}")

        print("\nComandos: move <uX> <x> <y> | fire <uX> <arma> <uY> | dive <uX> <prof> | surface <uX> | sonar <uX> | exit")
        user_input = input("\nTankScript CLI > ").strip()

        if user_input.lower() in ("exit", "quit"):
            break

        if user_input:
            try:
                in_lexer = Lexer(user_input)
                in_tokens = in_lexer.tokenize()
                in_parser = Parser(in_tokens)
                stmt = in_parser.parse_statement()

                print("\n--- AÇÃO DO JOGADOR ---")
                interpreter.execute_statement(stmt)
            except Exception as err:
                print(f"[ERRO]: {err}")

        # Turno da IA
        print("\n--- TURNO DA IA (RED) ---")
        ai_engine.compute_turn(interpreter, player_team)

        input("\nPressione [ENTER] para o próximo turno...")
        turn += 1

if __name__ == "__main__":
    main()