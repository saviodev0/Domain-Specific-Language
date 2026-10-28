import subprocess
import sys
from pathlib import Path

import pytest

from tankscript.interpreter import Interpreter
from tankscript.lexer import Lexer
from tankscript.parser import Parser
from tankscript.semantico import ErroSemantico, analisar


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_PROGRAMS = [
    *sorted((PROJECT_ROOT / "examples").glob("*.tank")),
    PROJECT_ROOT / "scripts" / "battle.tank",
]
SEMANTIC_INVALID_EXAMPLES = sorted((PROJECT_ROOT / "examples" / "invalidos_semanticos").glob("*.tank"))

UNIDADES = """
tank Alpha { hp 100 gun Cannon { damage 40 } }
submarine Shark { hp 80 torpedo T1 { damage 70 } }
"""


def erros(source):
    with pytest.raises(ErroSemantico) as excinfo:
        analisar(source)
    return excinfo.value.erros


@pytest.mark.parametrize("path", VALID_PROGRAMS, ids=lambda path: path.name)
def test_valid_programs_have_no_semantic_errors(path):
    analisar(path.read_text(encoding="utf-8"))


def test_symbol_table_records_units_weapons_teams_and_battles():
    resultado = analisar(UNIDADES + "team Blue { Alpha } team Red { Shark } battle War { Blue vs Red }")

    assert resultado.unidades["Alpha"].tipo == "tank"
    assert resultado.unidades["Shark"].armas == {"T1": "torpedo"}
    assert resultado.equipes == {"Blue": ["Alpha"], "Red": ["Shark"]}
    assert resultado.batalhas == {"War"}


def test_declarations_may_appear_after_their_use():
    analisar("move Alpha 1 2 tank Alpha { hp 1 }")


@pytest.mark.parametrize(
    ("source", "mensagem"),
    [
        ("move Ghost 1 2", "Linha 4, coluna 6: unidade 'Ghost' não declarada"),
        ("sonar Ghost", "unidade 'Ghost' não declarada"),
        ("attack Alpha Ghost", "unidade 'Ghost' não declarada"),
        ("fire Alpha T1 Shark", "'Alpha' não possui a arma 'T1'"),
        ("dive Alpha 10", "'dive' só vale para submarinos, e 'Alpha' é tank"),
        ("surface Alpha", "'surface' só vale para submarinos, e 'Alpha' é tank"),
        ("tank Beta { hp 1 } attack Beta Alpha", "'Beta' não tem armas para atacar"),
        ("tank Alpha { hp 1 }", "unidade 'Alpha' já declarada"),
        ("tank Beta { gun G { } gun G { } }", "arma 'G' já declarada em 'Beta'"),
        ("tank Beta { hp 1 hp 2 }", "propriedade 'hp' repetida em tank 'Beta'"),
        ("tank Beta { armr 1 }", "propriedade 'armr' não existe em tank 'Beta'"),
        ("tank Beta { depth 10 }", "propriedade 'depth' não existe em tank 'Beta'"),
        ("tank Beta { gun G { speed 1 } }", "propriedade 'speed' não existe em gun 'G'"),
        ("tank Beta { hp 10.5 }", "'hp' deve ser inteiro, mas recebeu 10.5"),
        ("tank Beta { gun G { ammo 2.5 } }", "'ammo' deve ser inteiro, mas recebeu 2.5"),
        ("team Blue { Ghost }", "unidade 'Ghost' não declarada"),
        ("team Blue { Alpha Alpha }", "unidade 'Alpha' repetida na equipe 'Blue'"),
        ("team Blue { Alpha } team Red { Alpha }", "unidade 'Alpha' já pertence à equipe 'Blue'"),
        ("team Blue { Alpha } team Blue { Shark }", "equipe 'Blue' já declarada"),
        ("team Blue { Alpha } battle War { Blue vs Red }", "equipe 'Red' não declarada"),
        ("team Blue { Alpha } battle War { Blue vs Blue }", "a equipe 'Blue' não pode enfrentar a si mesma"),
        (
            "team Blue { Alpha } team Red { Shark } battle W { Blue vs Red } battle W { Red vs Blue }",
            "batalha 'W' já declarada",
        ),
        ("if Alpha > 1 { sonar Alpha }", "'Alpha' sozinho não tem valor; use unidade.propriedade"),
        ("if Ghost.hp > 1 { sonar Alpha }", "unidade 'Ghost' não declarada"),
        ("if Alpha.alcance > 1 { sonar Alpha }", "propriedade 'alcance' não pode ser consultada"),
        ('if Alpha.hp > "muito" { sonar Alpha }', "'>' compara números, mas recebeu número e texto"),
        ('if "a" < "b" { sonar Alpha }', "'<' compara números, mas recebeu texto e texto"),
        ('if "a" == 1 { sonar Alpha }', "'==' compara valores do mesmo tipo, mas recebeu texto e número"),
        ("repeat 2 { if 1 == 1 { dive Alpha 3 } }", "'dive' só vale para submarinos"),
    ],
)
def test_semantic_errors_are_reported_with_location(source, mensagem):
    encontrados = erros(UNIDADES + source)

    assert any(mensagem in erro for erro in encontrados), encontrados
    assert all(erro.startswith("Linha ") for erro in encontrados)


def test_all_semantic_errors_are_reported_in_source_order():
    encontrados = erros("move Ghost 1 2\nsonar Phantom\n")

    assert encontrados == [
        "Linha 1, coluna 6: unidade 'Ghost' não declarada",
        "Linha 2, coluna 7: unidade 'Phantom' não declarada",
    ]


def test_syntax_errors_stop_before_semantic_analysis():
    with pytest.raises(SyntaxError, match=r"Linha 1, coluna \d+"):
        analisar("move Ghost 1")


@pytest.mark.parametrize("path", SEMANTIC_INVALID_EXAMPLES, ids=lambda path: path.name)
def test_semantic_cli_rejects_invalid_examples(path):
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "semantico.py"), str(path)],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        check=False,
    )

    assert result.returncode == 1
    assert "Erro semântico: Linha" in result.stderr


def test_delivery_has_three_semantically_invalid_programs():
    assert len(SEMANTIC_INVALID_EXAMPLES) == 3


def test_radar_is_readable_in_conditions():
    source = "tank Alpha { radar 70 } if Alpha.radar > 50 { move Alpha 5 5 }"
    analisar(source)
    interpreter = Interpreter(Parser(Lexer(source).tokenize()).parse())
    for declaration in interpreter.ast["declarations"]:
        interpreter.execute_declaration(declaration)
    for statement in interpreter.ast["statements"]:
        interpreter.execute_statement(statement)

    assert (interpreter.units["Alpha"].x, interpreter.units["Alpha"].y) == (5, 5)
