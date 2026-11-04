"""Cenários de erro e de regra do jogo, um por regra. Cada cenário monta uma situação mínima,
joga um turno e confere a mensagem e o estado resultante."""

import socket
import threading
from http.server import ThreadingHTTPServer

import pytest

from src.servidor import Manipulador
from tankscript.partida import LIMITE_DE_TURNOS, ErroDaPartida, Partida
from tankscript.semantico import ErroSemantico


def partida(unidades, azul, vermelho, posicoes="", ia=False):
    jogo = Partida(f"{unidades}\nteam Azul {{ {azul} }}\nteam Vermelho {{ {vermelho} }}\n"
                   f"battle B {{ Azul vs Vermelho }}\n{posicoes}")
    if not ia:
        jogo.ia = None
    return jogo


def mensagens(eventos, origem="jogador"):
    return [m for e in eventos if origem in (None, e["origem"]) for m in e["mensagens"]]


def erros_do_turno(jogo, codigo):
    with pytest.raises(ErroSemantico) as excinfo:
        jogo.jogar_turno(codigo)
    return excinfo.value.erros


ALVO_LONGE = "tank Alvo { gun G }"


# ---------- erros de programa: barrados antes de executar ----------

@pytest.mark.parametrize(
    ("codigo", "mensagem"),
    [
        ("fire Rex G Rex", "'Rex' não pode atacar a si mesmo"),
        ("fire Rex G Max", "'Max' é da mesma equipe de 'Rex' (Azul)"),
        ("attack Rex Max", "'Max' é da mesma equipe de 'Rex' (Azul)"),
        ("dive Orca 0", "a profundidade do 'dive' precisa ser maior que 0"),
        ("dive Rex 10", "'dive' só vale para submarinos"),
        ("move Alvo 10 10", "'Alvo' não é da sua equipe"),
        ("move Rex 200 10", "x = 200 está fora do mapa"),
        ("fire Rex Missil Alvo", "'Rex' não possui a arma 'Missil'"),
        ('if Rex.hp > "alto" { sonar Rex }', "'>' compara números"),
        ("tank Novo { }", "declarações ficam no cenário"),
    ],
)
def test_invalid_turn_programs_are_rejected_with_location(codigo, mensagem):
    jogo = partida(f"tank Rex {{ gun G }} tank Max {{ gun G }} submarine Orca {{ }} {ALVO_LONGE}",
                   "Rex Max Orca", "Alvo", "move Alvo 190 90")

    erros = erros_do_turno(jogo, codigo)

    assert any(mensagem in erro and erro.startswith("Linha 1, coluna") for erro in erros), erros
    assert jogo.turno == 0


# ---------- movimento e terreno ----------

def test_move_beyond_speed_stops_halfway():
    jogo = partida(f"tank Rex {{ }} {ALVO_LONGE}", "Rex", "Alvo", "move Rex 10 50 move Alvo 190 90")

    eventos = jogo.jogar_turno("move Rex 110 50")

    assert "[MOVE LIMITADO] Rex anda até 30 por turno e parou em (40, 50)" in mensagens(eventos)


def test_movement_budget_is_shared_by_all_moves_of_the_turn():
    jogo = partida(f"tank Rex {{ }} {ALVO_LONGE}", "Rex", "Alvo", "move Rex 10 50 move Alvo 190 90")

    eventos = jogo.jogar_turno("repeat 5 { move Rex 30 50 move Rex 10 50 }")

    assert mensagens(eventos).count("[SEM MOVIMENTO] Rex já andou 30 neste turno") >= 1


def test_tank_cannot_jump_over_an_island():
    jogo = partida(f"tank Rex {{ }} {ALVO_LONGE}", "Rex", "Alvo", "move Rex 70 25 move Alvo 190 90")

    eventos = jogo.jogar_turno("move Rex 95 25")

    assert "[COLISÃO] Rex encontrou uma Ilha/Montanha no caminho e parou em (79, 25)" in mensagens(eventos)


def test_move_straight_into_an_island_is_blocked():
    jogo = partida(f"submarine Orca {{ }} {ALVO_LONGE}", "Orca", "Alvo", "move Orca 79 25 move Alvo 190 90")

    eventos = jogo.jogar_turno("move Orca 85 25")

    assert "[COLISÃO] Orca tentou mover para uma Ilha/Montanha e foi bloqueado!" in mensagens(eventos)
    assert jogo.interpretador.units["Orca"].x == 79


def test_initial_placement_ignores_islands_on_the_way():
    jogo = partida(f"tank Rex {{ }} {ALVO_LONGE}", "Rex", "Alvo", "move Rex 100 40 move Alvo 190 90")

    assert (jogo.interpretador.units["Rex"].x, jogo.interpretador.units["Rex"].y) == (100, 40)


def test_submarine_cannot_dive_in_shallow_water():
    jogo = partida(f"submarine Orca {{ }} {ALVO_LONGE}", "Orca", "Alvo", "move Orca 125 15 move Alvo 190 90")

    eventos = jogo.jogar_turno("dive Orca 30")

    assert "[DIVE IMPOSSÍVEL] Orca está em Água Rasa (~) e não pode submergir!" in mensagens(eventos)


# ---------- combate ----------

def combate(atacante, alvo, posicoes, codigo, **ajustes):
    jogo = partida(f"{atacante} {alvo}", atacante.split()[1], alvo.split()[1], posicoes)
    for nome, valores in ajustes.items():
        for atributo, valor in valores.items():
            setattr(jogo.interpretador.units[nome], atributo, valor)
    return jogo, mensagens(jogo.jogar_turno(codigo))


def test_cannot_fire_at_what_the_team_does_not_see():
    _, saida = combate("tank Rex { gun G }", "tank Alvo { gun G }", "move Rex 10 50 move Alvo 60 50", "fire Rex G Alvo")

    assert saida == ["[SEM VISÃO] Rex não enxerga Alvo; aproxime-se ou use o sonar"]


def test_target_out_of_range_is_a_miss():
    jogo, _ = combate("tank Rex { gun G }", "tank Alvo { gun G }", "move Rex 10 50 move Alvo 90 50", "")
    jogo.interpretador.units["Alvo"].sonar_ping_turns = 2

    eventos = jogo.jogar_turno("fire Rex G Alvo")

    assert "[FIRE ERROU] Alvo fora do alcance!" in mensagens(eventos)


def test_weapon_cooldown_and_ammo():
    jogo, saida = combate("tank Rex { gun G }", "tank Alvo { gun G }", "move Rex 100 50 move Alvo 110 50",
                          "fire Rex G Alvo\nfire Rex G Alvo")
    assert saida[1] == "[RECARREGANDO] G em cooldown por mais 1 turno(s)!"

    jogo.interpretador.units["Rex"].weapons[0]["ammo"] = 0
    assert "[SEM MUNIÇÃO] G está sem munição disponível!" in mensagens(jogo.jogar_turno("fire Rex G Alvo"))


def test_damage_is_weapon_damage_minus_armor_and_halved_in_ruins():
    _, saida = combate("tank Rex { gun G }", "tank Alvo { gun G }", "move Rex 60 55 move Alvo 70 55", "fire Rex G Alvo")
    assert "[FIRE SUCESSO] Rex usou G em Alvo! Dano: 25 (HP: 95) [Munição: 5]" in saida

    _, saida = combate("tank Rex { gun G }", "tank Alvo { gun G }", "move Rex 40 55 move Alvo 55 55", "fire Rex G Alvo")
    assert "[FIRE SUCESSO] Rex usou G em Alvo! Dano: 12 (HP: 108) [Munição: 5]" in saida


def test_aircraft_does_not_take_cover_in_ruins():
    _, saida = combate("tank Rex { gun G }", "aircraft Alvo { missile M }", "move Rex 40 55 move Alvo 55 55",
                       "fire Rex G Alvo")

    assert "[FIRE SUCESSO] Rex usou G em Alvo! Dano: 35 (HP: 35) [Munição: 5]" in saida


def test_attack_uses_the_first_ready_weapon():
    _, saida = combate("tank Rex { gun A gun B }", "tank Alvo { gun G }", "move Rex 100 50 move Alvo 110 50",
                       "attack Rex Alvo\nattack Rex Alvo")

    assert [m.split("!")[0] for m in saida] == ["[FIRE SUCESSO] Rex usou A em Alvo", "[FIRE SUCESSO] Rex usou B em Alvo"]


def test_exposed_submarine_takes_double_damage_and_cannot_hide_again():
    jogo = partida("submarine Orca { torpedo T } tank Alvo { gun G }", "Orca", "Alvo",
                   "move Orca 100 50 move Alvo 110 50 dive Orca 30")
    assert "[ALERTA] Orca atirou submerso e subirá exposto no próximo turno!" in " ".join(
        mensagens(jogo.jogar_turno("fire Orca T Alvo")))

    eventos = jogo.jogar_turno("dive Orca 30")
    assert "[DIVE BLOQUEADO] Orca está EXPOSTO e só pode submergir no próximo turno!" in mensagens(eventos)

    jogo.interpretador.teams["Azul"], jogo.interpretador.teams["Vermelho"] = ["Alvo"], ["Orca"]
    jogo.interpretador.execute_statement({"type": "FireStatement", "attacker": "Alvo", "weapon": "G", "target": "Orca"})
    assert jogo.interpretador.units["Orca"].hp == 90 - (40 - 10) * 2


def test_friendly_fire_is_also_blocked_at_runtime():
    jogo = partida(f"tank Rex {{ gun G }} tank Max {{ }} {ALVO_LONGE}", "Rex Max", "Alvo",
                   "move Rex 10 50 move Max 20 50 move Alvo 190 90")
    jogo.interpretador.iniciar("jogador")

    jogo.interpretador.execute_statement({"type": "FireStatement", "attacker": "Rex", "weapon": "G", "target": "Max"})

    assert jogo.interpretador.eventos[-1]["mensagens"] == ["[FIRE FALHOU] Rex não atira na própria equipe!"]
    assert jogo.interpretador.units["Max"].hp == 120


# ---------- sonar e névoa ----------

def test_sonar_recharges_and_reveals_the_emitter():
    jogo = partida("tank Rex { gun G } tank Alvo { gun G }", "Rex", "Alvo", "move Rex 10 50 move Alvo 40 50")

    saida = mensagens(jogo.jogar_turno("sonar Rex\nfire Rex G Alvo\nsonar Rex"))

    assert "-> [PING] Unidade detectada: Alvo na posição (40, 50)!" in saida
    assert any(m.startswith("[FIRE SUCESSO]") for m in saida)
    assert "[SONAR RECARREGANDO] Rex só pode usar o sonar de novo em 2 turno(s)" in saida
    assert jogo.interpretador.units["Rex"].sonar_ping_turns > 0


def test_enemy_sonar_noise_lasts_until_the_players_next_turn():
    jogo = partida("tank Rex { gun G } aircraft Corvo { missile M }", "Rex", "Corvo",
                   "move Rex 10 50 move Corvo 60 50", ia=True)
    jogo.ia.compute_turn = lambda interpretador, alvos: interpretador.execute_statement(
        {"type": "SonarStatement", "unit": "Corvo"})
    jogo.jogar_turno("")
    jogo.ia = None

    saida = mensagens(jogo.jogar_turno("fire Rex G Corvo"))

    assert any(m.startswith("[FIRE SUCESSO] Rex usou G em Corvo") for m in saida), saida


def test_conditions_cannot_read_enemies_in_the_fog():
    jogo = partida(f"tank Rex {{ }} {ALVO_LONGE}", "Rex", "Alvo", "move Rex 10 50 move Alvo 170 80")

    eventos = jogo.jogar_turno("if Alvo.x > 150 { move Rex 30 50 }")

    assert "[SEM VISÃO] Alvo está fora de vista; a condição conta como falsa" in mensagens(eventos)
    assert jogo.interpretador.units["Rex"].x == 10


def test_conditions_can_read_visible_enemies_and_own_units():
    jogo = partida(f"tank Rex {{ }} {ALVO_LONGE}", "Rex", "Alvo", "move Rex 10 50 move Alvo 30 50")

    jogo.jogar_turno("if Alvo.x == 30 { if Rex.hp == 120 { move Rex 20 50 } }")

    assert jogo.interpretador.units["Rex"].x == 20


def test_hidden_enemies_do_not_leak_to_the_browser():
    jogo = partida("tank Rex { } tank Alvo { gun G }", "Rex", "Alvo", "move Rex 10 50 move Alvo 170 80", ia=True)

    eventos = jogo.jogar_turno("")

    ia = [e for e in eventos if e["origem"] == "ia"]
    assert ia and all(m == "Movimento inimigo na névoa" for e in ia for m in e["mensagens"])
    assert all(e["instrucao"] == {} for e in ia)
    alvo = next(u for u in eventos[-1]["estado"]["unidades"] if u["nome"] == "Alvo")
    assert (alvo["x"], alvo["y"], alvo["hp"]) == (None, None, None)


# ---------- fim de partida ----------

def test_destroying_every_enemy_wins():
    jogo, _ = combate("tank Rex { gun G }", "tank Alvo { gun G }", "move Rex 100 50 move Alvo 110 50",
                      "fire Rex G Alvo", Alvo={"hp": 10})

    assert jogo.vencedor == "Azul"
    with pytest.raises(ErroDaPartida, match="terminou"):
        jogo.jogar_turno("")


def test_draw_when_nobody_can_hurt_anyone():
    jogo = partida("aircraft Hawk { } submarine Orca { }", "Hawk", "Orca", "move Hawk 10 50 move Orca 180 50")

    assert jogo.resumo()["empate"] is True
    assert jogo.motivo_do_empate == "nenhum lado tem mais armas capazes de ferir o adversário"
    with pytest.raises(ErroDaPartida, match="empatada"):
        jogo.jogar_turno("")


def test_torpedoes_cannot_end_a_match_against_aircraft():
    jogo = partida("submarine Orca { torpedo T } aircraft Hawk { }", "Orca", "Hawk")

    assert jogo.motivo_do_empate is not None


def test_draw_after_the_turn_limit():
    jogo = partida("tank Rex { gun G } tank Alvo { gun G }", "Rex", "Alvo", "move Rex 10 10 move Alvo 190 90")
    for _ in range(LIMITE_DE_TURNOS):
        jogo.jogar_turno("")

    assert jogo.motivo_do_empate == f"o limite de {LIMITE_DE_TURNOS} turnos acabou"


# ---------- servidor ----------

@pytest.mark.parametrize("cabecalho", [b"Content-Length: -1", b"Content-Length: 999999999", b"Content-Length: abc"])
def test_server_rejects_bad_request_sizes_without_hanging(cabecalho):
    http = ThreadingHTTPServer(("127.0.0.1", 0), Manipulador)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    try:
        with socket.create_connection(http.server_address, timeout=3) as conexao:
            conexao.sendall(b"POST /api/exercito HTTP/1.1\r\nHost: x\r\n" + cabecalho + b"\r\n\r\n")
            assert conexao.recv(64).startswith(b"HTTP/1.0 400")
    finally:
        http.shutdown()
        http.server_close()
