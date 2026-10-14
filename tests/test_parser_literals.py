import pytest

from tankscript.interpreter import Interpreter
from tankscript.lexer import Lexer
from tankscript.parser import Parser
from tankscript.renderer import GridRenderer


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_float_properties_and_coordinates_execute():
    ast = parse("tank Alpha { radar 12.5 } move Alpha 12.5 20.25")

    assert ast["declarations"][0]["properties"]["radar"] == 12.5
    assert ast["statements"][0]["x"] == 12.5
    assert ast["statements"][0]["y"] == 20.25

    interpreter = Interpreter(ast, renderer=GridRenderer())
    interpreter.execute_declaration(ast["declarations"][0])
    interpreter.execute_statement(ast["statements"][0])

    assert (interpreter.units["Alpha"].x, interpreter.units["Alpha"].y) == (12.5, 20.25)


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ('3.14 > 3.13', True),
        ('"same" == "same"', True),
        ('"same" == "different"', False),
    ],
)
def test_float_and_string_literals_work_in_conditions(condition, expected):
    ast = parse(f"if {condition} {{ sonar Alpha }}")
    interpreter = Interpreter(ast)

    assert interpreter.evaluate_expression(ast["statements"][0]["condition"]) is expected


def test_repeat_count_remains_integer():
    with pytest.raises(SyntaxError, match="Esperado token NUMBER"):
        parse("repeat 1.5 { surface Alpha }")