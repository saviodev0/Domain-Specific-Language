import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from src.servidor import Manipulador
from tankscript.catalogo import ORCAMENTO, custo
from tankscript.partida import (
    LIMITE_DE_INSTRUCOES,
    Partida,
    criar_arena,
    erros_do_programa,
    verificar_exercito,
)
from tankscript.semantico import ErroSemantico

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_PROGRAMS = [
    *sorted((PROJECT_ROOT / "examples").glob("*.tank")),
    PROJECT_ROOT / "scripts" / "battle.tank",
]
BATALHA = (PROJECT_ROOT / "scripts" / "battle.tank").read_text(encoding="utf-8")
EXERCITO = "tank Rex { gun Canhao gun Reserva }\naircraft Hawk { missile Ferrao }\n"


def erros_do_turno(partida, codigo):
    with pytest.raises((SyntaxError, ErroSemantico)) as excinfo:
        partida.jogar_turno(codigo)
    return erros_do_programa(excinfo.value)


@pytest.mark.parametrize("path", VALID_PROGRAMS, ids=lambda path: path.name)
def test_every_valid_program_starts_a_match(path):
    partida = Partida(path.read_text(encoding="utf-8"))

    assert partida.estado()["unidades"]


def test_scenario_events_carry_source_lines_and_state():
    partida = Partida(BATALHA)

    assert partida.resumo()["jogador"] == "Blue"
    assert partida.resumo()["inimigo"] == "Red"
    assert [evento["tipo"] for evento in partida.eventos_do_cenario] == [
        "MoveStatement",
        "MoveStatement",
        "DiveStatement",
    ]
    assert [evento["linha"] for evento in partida.eventos_do_cenario] == [21, 22, 23]
    movimento = partida.eventos_do_cenario[0]
    assert movimento["mensagens"] == ["[MOVE] Tiger1 moveu para (20, 20)"]
    tiger = next(u for u in movimento["estado"]["unidades"] if u["nome"] == "Tiger1")
    assert (tiger["x"], tiger["y"], tiger["lado"]) == (20, 20, "jogador")


def test_submerged_enemy_is_hidden_from_the_player():
    partida = Partida(BATALHA)
    shark = next(u for u in partida.estado()["unidades"] if u["nome"] == "Shark1")

    assert shark["profundidade"] == 40
    assert shark["visivel"] is False


def test_turn_runs_player_program_then_enemy_ai():
    partida = Partida(BATALHA)
    eventos = partida.jogar_turno("repeat 2 { move Tiger1 40 20 }\nif Tiger1.hp > 50 { sonar Tiger1 }")

    assert eventos[0]["tipo"] == "InicioDoTurno"
    jogador = [(e["tipo"], e["linha"]) for e in eventos if e["origem"] == "jogador"]
    assert jogador == [
        ("RepeatStatement", 1),
        ("MoveStatement", 1),
        ("MoveStatement", 1),
        ("IfStatement", 2),
        ("SonarStatement", 2),
    ]
    assert any(e["origem"] == "ia" for e in eventos)
    assert partida.turno == 1


@pytest.mark.parametrize(
    ("codigo", "mensagem"),
    [
        ("move Shark1 10 10", "Linha 1, coluna 6: 'Shark1' não é da sua equipe; você comanda: Tiger1"),
        ("tank Novo { hp 1 }", "Linha 1, coluna 1: declarações ficam no cenário"),
        ("move Tiger1 500 10", "Linha 1, coluna 13: x = 500 está fora do mapa (de 0 a 199)"),
        ("move Tiger1 10 100", "Linha 1, coluna 16: y = 100 está fora do mapa (de 0 a 99)"),
        ("fire Tiger1 T1 Shark1", "'Tiger1' não possui a arma 'T1'"),
        ("move Ghost 1 1", "unidade 'Ghost' não declarada"),
    ],
)
def test_invalid_turns_are_rejected_without_changing_the_match(codigo, mensagem):
    partida = Partida(BATALHA)
    antes = partida.estado()

    erros = erros_do_turno(partida, codigo)

    assert any(mensagem in erro["mensagem"] for erro in erros), erros
    assert all(erro["linha"] == 1 for erro in erros)
    assert partida.estado() == antes
    assert partida.turno == 0


def test_syntax_errors_are_reported_with_position():
    erros = erros_do_turno(Partida(BATALHA), "move Tiger1 10")

    assert erros[0]["fase"] == "sintático"
    assert (erros[0]["linha"], erros[0]["coluna"]) == (1, 15)


def test_long_loops_stop_at_the_instruction_limit():
    partida = Partida("tank A { } repeat 100 { repeat 100 { move A 1 1 } }")

    assert partida.eventos_do_cenario[-1]["tipo"] == "Aviso"
    assert str(LIMITE_DE_INSTRUCOES) in partida.eventos_do_cenario[-1]["mensagens"][0]


def test_match_without_teams_lets_the_player_command_every_unit():
    partida = Partida("tank A { } tank B { }")

    assert partida.comandaveis == ["A", "B"]
    assert partida.vencedor is None
    partida.jogar_turno("move B 30 30")


def test_destroying_the_enemy_team_ends_the_match():
    partida = Partida(BATALHA)
    partida.interpretador.units["Shark1"].hp = 0

    assert partida.vencedor == "Blue"
    with pytest.raises(Exception, match="terminou"):
        partida.jogar_turno("sonar Tiger1")


def test_units_get_the_fixed_attributes_of_their_type():
    partida = Partida("tank T { gun G } aircraft A { missile M } submarine S { torpedo P }")
    unidades = {u["nome"]: u for u in partida.estado()["unidades"]}

    assert (unidades["T"]["hp"], unidades["T"]["armadura"], unidades["T"]["velocidade"]) == (120, 15, 30)
    assert (unidades["A"]["hp"], unidades["A"]["radar"]) == (70, 100)
    assert unidades["S"]["armas"][0] == {
        "nome": "P", "tipo": "torpedo", "dano": 70, "alcance": 80, "municao": 3, "recarga": 0,
    }


def test_movement_per_turn_is_limited_by_speed():
    partida = Partida("tank T { } team A { T } move T 0 0")
    eventos = partida.jogar_turno("move T 100 0\nmove T 100 0")

    mensagens = [m for e in eventos for m in e["mensagens"]]
    assert "[MOVE LIMITADO] T anda até 30 por turno e parou em (30, 0)" in mensagens
    assert "[SEM MOVIMENTO] T já andou 30 neste turno" in mensagens
    assert partida.interpretador.units["T"].x == 30


def test_aircraft_flies_over_islands_and_dodges_torpedoes():
    partida = Partida("aircraft A { } tank T { } submarine S { torpedo P } team X { A T S } move A 50 20 move T 50 20")
    partida.jogar_turno("move A 80 20\nmove T 80 20")
    unidades = partida.interpretador.units
    assert (unidades["A"].x, unidades["A"].y) == (80, 20)
    assert (unidades["T"].x, unidades["T"].y) == (50, 20)

    eventos = partida.jogar_turno("move S 60 20\nfire S P A")
    assert "[FIRE INEFICAZ] Torpedos não atingem aeronaves!" in [m for e in eventos for m in e["mensagens"]]


def test_only_torpedoes_hit_a_submerged_submarine():
    partida = Partida("aircraft A { missile M } submarine S { } team X { A S } dive S 20")
    eventos = partida.jogar_turno("fire A M S")

    assert "[FIRE INEFICAZ] Só torpedos atingem submarinos submersos!" in [m for e in eventos for m in e["mensagens"]]


def test_arena_builds_an_enemy_fleet_with_the_same_budget():
    partida = criar_arena(EXERCITO, semente=7)

    assert partida.resumo()["jogador"] == "Jogador"
    assert partida.comandaveis == ["Rex", "Hawk"]
    inimigos = [u for u in partida.estado_inicial["unidades"] if u["lado"] == "inimigo"]
    gasto = sum(custo(u["tipo"], len(u["armas"])) for u in inimigos)
    assert ORCAMENTO - 3 < gasto <= ORCAMENTO
    assert all(u["x"] == 180 for u in inimigos)
    assert {u["x"] for u in partida.estado_inicial["unidades"] if u["lado"] == "jogador"} == {10}
    assert partida.codigo_do_inimigo.splitlines()[0].split()[0] in ("tank", "submarine", "aircraft")


def test_enemy_names_never_clash_with_the_player():
    partida = criar_arena("tank Brutus { } tank Rochedo { } tank Bastiao { }", semente=2)

    nomes = [u["nome"] for u in partida.estado_inicial["unidades"]]
    assert len(nomes) == len(set(nomes))


@pytest.mark.parametrize(
    ("codigo", "mensagem"),
    [
        ("", "Linha 1, coluna 1: declare pelo menos uma unidade"),
        ("tank A { } tank B { } tank C { } tank D { }", "Linha 1, coluna 34: orçamento estourado: o exército chega a 16 de 12 pontos"),
        ("tank A { }\nmove A 1 1", "Linha 2, coluna 1: o cenário só monta o exército"),
        ("tank A { }\nteam X { A }", "Linha 2, coluna 1: na arena você só declara unidades"),
        ("tank A { hp 999 }", "'hp' é fixo: todo tank tem hp 120"),
    ],
)
def test_arena_rejects_invalid_armies(codigo, mensagem):
    with pytest.raises(ErroSemantico) as excinfo:
        criar_arena(codigo)

    assert any(mensagem in erro for erro in excinfo.value.erros), excinfo.value.erros


def test_army_check_reports_cost_while_typing():
    resultado = verificar_exercito(EXERCITO)

    assert resultado["custo"] == 9
    assert resultado["erros"] == []
    assert resultado["unidades"][0] == {"nome": "Rex", "tipo": "tank", "armas": ["gun", "gun"], "custo": 5}
    assert verificar_exercito("tank {")["erros"][0]["fase"] == "sintático"


@pytest.fixture
def servidor():
    http = ThreadingHTTPServer(("127.0.0.1", 0), Manipulador)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{http.server_address[1]}"
    http.shutdown()
    http.server_close()


def requisitar(url, codigo=None):
    dados = None if codigo is None else json.dumps({"codigo": codigo}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=dados)) as resposta:
            return resposta.status, json.loads(resposta.read())
    except urllib.error.HTTPError as erro:
        return erro.code, json.loads(erro.read())


def test_server_plays_an_arena_match_over_http(servidor):
    status, partida = requisitar(f"{servidor}/api/partidas", EXERCITO)
    assert status == 201
    assert partida["mapa"]["largura"] == 20
    assert partida["comandaveis"] == ["Rex", "Hawk"]
    assert partida["codigo_do_inimigo"]

    status, turno = requisitar(f"{servidor}/api/partidas/{partida['id']}/turnos", "sonar Rex")
    assert status == 200
    assert turno["turno"] == 1

    inimigo = partida["codigo_do_inimigo"].split()[1]
    status, resposta = requisitar(f"{servidor}/api/partidas/{partida['id']}/turnos", f"move {inimigo} 1 1")
    assert status == 422
    assert resposta["erros"][0]["linha"] == 1


def test_server_reports_errors_and_serves_the_page(servidor):
    status, resposta = requisitar(f"{servidor}/api/partidas", "tank A { torpedo T }")
    assert status == 422
    assert resposta["erros"][0]["fase"] == "semântico"

    status, resposta = requisitar(f"{servidor}/api/partidas/inexistente/turnos", "sonar A")
    assert status == 400

    status, resposta = requisitar(f"{servidor}/api/exercito", EXERCITO)
    assert (status, resposta["custo"]) == (200, 9)

    status, catalogo = requisitar(f"{servidor}/api/catalogo")
    assert status == 200
    assert catalogo["unidades"]["aircraft"]["armas"] == ["missile"]

    with urllib.request.urlopen(f"{servidor}/") as resposta:
        assert b"phaser" in resposta.read()
