import subprocess
import sys
from pathlib import Path

import pytest

from tankscript.arvore import arvore_como_texto
from tankscript.lexer import Lexer
from tankscript.parser import Parser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_PROGRAMS = [
    *sorted((PROJECT_ROOT / "examples").glob("*.tank")),
    PROJECT_ROOT / "scripts" / "battle.tank",
]
MALFORMED_SOURCES = [
    "move Alpha 1",
    "attack Alpha",
    "fire Alpha Cannon",
    "dive Alpha",
    "surface",
    "sonar",
    "repeat { sonar Alpha }",
    "if Alpha.hp { sonar Alpha }",
    "if Alpha.hp == { sonar Alpha }",
    "if 1 == 1 { sonar Alpha",
    "repeat 1 { tank Alpha {} }",
    "move Alpha 1 2 +",
    "move Alpha 1 2 extra",
    "tank Alpha { hp }",
    "tank Alpha { hp 1",
    "team Blue {",
    "battle War { Blue vs Red",
    "if 1 < 2 < 3 { sonar Alpha }",
]


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


@pytest.mark.parametrize(
    ("source", "statement_type"),
    [
        ("move Alpha 1 2", "MoveStatement"),
        ("attack Alpha Beta", "AttackStatement"),
        ("fire Alpha Cannon Beta", "FireStatement"),
        ("dive Alpha 10", "DiveStatement"),
        ("surface Alpha", "SurfaceStatement"),
        ("sonar Alpha", "SonarStatement"),
    ],
)
def test_standalone_statements_are_parsed(source, statement_type):
    statement = Parser(Lexer(source).tokenize()).parse_statement()

    assert statement["type"] == statement_type


def test_program_preserves_statement_order_and_arguments_in_ast():
    ast = parse(
        "tank Alpha { hp 100 gun Cannon { damage 20 } } "
        "move Alpha 1 2 sonar Alpha"
    )

    assert ast["type"] == "Program"
    assert ast["declarations"][0]["properties"] == {"hp": 100}
    assert ast["declarations"][0]["weapons"][0]["name"] == "Cannon"
    assert [statement["type"] for statement in ast["statements"]] == [
        "MoveStatement",
        "SonarStatement",
    ]
    assert ast["statements"][0] == {
        "type": "MoveStatement",
        "unit": "Alpha",
        "x": 1,
        "y": 2,
    }


def test_comparison_and_member_access_form_hierarchical_ast():
    ast = parse('if Alpha.hp > 20 { sonar Alpha }')
    condition = ast["statements"][0]["condition"]

    assert condition == {
        "type": "BinaryExpression",
        "operator": ">",
        "left": {"type": "MemberAccess", "unit": "Alpha", "property": "hp"},
        "right": {"type": "Literal", "value": 20},
    }


def test_if_and_repeat_blocks_are_recursively_nested():
    ast = parse('repeat 2 { if "ready" == "ready" { repeat 1 { sonar Alpha } } }')
    outer = ast["statements"][0]
    conditional = outer["body"][0]
    inner_repeat = conditional["body"][0]

    assert outer["type"] == "RepeatStatement"
    assert conditional["type"] == "IfStatement"
    assert inner_repeat == {
        "type": "RepeatStatement",
        "count": 1,
        "body": [{"type": "SonarStatement", "unit": "Alpha"}],
    }


@pytest.mark.parametrize("source", MALFORMED_SOURCES)
def test_malformed_syntax_is_rejected_with_line_and_column(source):
    with pytest.raises(SyntaxError, match=r"Linha \d+, coluna \d+"):
        parse(source)


def test_comparison_chaining_is_rejected():
    with pytest.raises(SyntaxError, match=r"Linha 1, coluna \d+"):
        parse("if 1 < 2 < 3 { sonar Alpha }")


def test_standalone_statement_rejects_trailing_tokens():
    parser = Parser(Lexer("sonar Alpha surface Beta").tokenize())

    with pytest.raises(SyntaxError, match=r"Linha 1, coluna \d+"):
        parser.parse_statement()


def test_existing_battle_script_parses_with_recursive_statements():
    script = PROJECT_ROOT / "scripts" / "battle.tank"
    ast = parse(script.read_text(encoding="utf-8"))

    assert ast["type"] == "Program"


@pytest.mark.parametrize("path", VALID_PROGRAMS, ids=lambda path: path.name)
def test_antlr_grammar_accepts_valid_programs(path):
    tree = arvore_como_texto(path.read_text(encoding="utf-8"))

    assert tree.startswith("(programa ")
    assert tree.endswith("<EOF>)")


@pytest.mark.parametrize("source", MALFORMED_SOURCES)
def test_antlr_grammar_rejects_what_the_manual_parser_rejects(source):
    with pytest.raises(SyntaxError, match=r"Linha \d+, coluna \d+"):
        arvore_como_texto(source)


def test_antlr_tree_shows_nested_blocks_and_member_access():
    tree = arvore_como_texto("repeat 2 { if Alpha.hp > 20 { sonar Alpha } }")

    assert tree == (
        "(programa (instrucao (repeticao repeat 2 (bloco { "
        "(instrucao (condicional if (comparacao (primario Alpha . hp) > "
        "(primario (numero 20))) (bloco { (instrucao (sonar sonar Alpha)) }))) }))) <EOF>)"
    )


def test_tree_cli_reports_syntax_errors_with_location(tmp_path):
    program = tmp_path / "invalido.tank"
    program.write_text("move Alpha 1", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "sintatico.py"), str(program)],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        check=False,
    )

    assert result.returncode == 1
    assert "Linha 1, coluna" in result.stderr
