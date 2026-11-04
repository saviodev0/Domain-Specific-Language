from tankscript.partida import Partida


def mensagens(eventos, origem="ia"):
    return [mensagem for evento in eventos if evento["origem"] == origem for mensagem in evento["mensagens"]]


def partida(unidades_jogador, unidades_ia, posicoes):
    jogador = " ".join(nome for nome, _ in unidades_jogador)
    ia = " ".join(nome for nome, _ in unidades_ia)
    declaracoes = "\n".join(declaracao for _, declaracao in [*unidades_jogador, *unidades_ia])
    movimentos = "\n".join(f"move {nome} {x} {y}" for nome, (x, y) in posicoes.items())
    return Partida(f"{declaracoes}\nteam Azul {{ {jogador} }}\nteam Vermelho {{ {ia} }}\n"
                   f"battle B {{ Azul vs Vermelho }}\n{movimentos}")


def test_ai_does_not_see_through_the_fog():
    jogo = partida([("Rex", "tank Rex { gun G }")], [("Brutus", "tank Brutus { gun G }")],
                   {"Rex": (10, 50), "Brutus": (180, 50)})

    eventos = jogo.jogar_turno("move Rex 10 50")

    assert not any("[FIRE" in mensagem for mensagem in mensagens(eventos))
    assert jogo.interpretador.units["Brutus"].x < 180


def test_ai_hunts_where_the_player_was_last_seen():
    jogo = partida([("Hawk", "aircraft Hawk { missile M }")], [("Brutus", "tank Brutus { gun G }")],
                   {"Hawk": (150, 20), "Brutus": (170, 20)})
    jogo.jogar_turno("move Hawk 150 20")
    assert jogo.ia.last_seen["Hawk"][:2] == (150, 20)

    jogo.jogar_turno("move Hawk 70 80")

    brutus = jogo.interpretador.units["Brutus"]
    assert brutus.x < 170


def test_ai_focuses_fire_on_the_unit_it_can_destroy():
    jogo = partida(
        [("Forte", "tank Forte { gun G }"), ("Fraco", "tank Fraco { gun G }")],
        [("Brutus", "tank Brutus { gun A gun B }")],
        {"Forte": (100, 40), "Fraco": (100, 60), "Brutus": (120, 50)},
    )
    jogo.interpretador.units["Fraco"].hp = 20

    eventos = jogo.jogar_turno("move Forte 100 40")

    assert any("Brutus usou A em Fraco" in mensagem for mensagem in mensagens(eventos))
    assert not jogo.interpretador.units["Fraco"].is_alive()


def test_ai_does_not_waste_torpedoes_on_aircraft():
    jogo = partida([("Hawk", "aircraft Hawk { missile M }")], [("Kraken", "submarine Kraken { torpedo T }")],
                   {"Hawk": (150, 50), "Kraken": (170, 50)})

    eventos = jogo.jogar_turno("move Hawk 130 50")

    assert not any("[FIRE" in mensagem for mensagem in mensagens(eventos))


def test_idle_submarine_dives_to_hide():
    jogo = partida([("Rex", "tank Rex { gun G }")], [("Kraken", "submarine Kraken { torpedo T }")],
                   {"Rex": (10, 50), "Kraken": (180, 50)})

    jogo.jogar_turno("move Rex 10 50")

    assert jogo.interpretador.units["Kraken"].depth > 0
