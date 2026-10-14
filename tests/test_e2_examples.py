import subprocess
import sys
from pathlib import Path

import pytest

from tankscript.lexer import Lexer
from tankscript.parser import Parser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_EXAMPLES = sorted((PROJECT_ROOT / "examples").glob("*.tank"))
INVALID_EXAMPLES = sorted((PROJECT_ROOT / "examples" / "invalidos").glob("*.tank"))


def test_delivery_has_three_valid_and_three_invalid_programs():
    assert len(VALID_EXAMPLES) == 3
    assert len(INVALID_EXAMPLES) == 3


@pytest.mark.parametrize("path", VALID_EXAMPLES, ids=lambda path: path.name)
def test_valid_examples_are_lexed_and_parsed(path):
    tokens = Lexer(path.read_text(encoding="utf-8")).tokenize()
    ast = Parser(tokens).parse()

    assert ast["type"] == "Program"


@pytest.mark.parametrize("path", INVALID_EXAMPLES, ids=lambda path: path.name)
def test_invalid_examples_fail_with_a_location(path):
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "lexico.py"), str(path)],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        check=False,
    )

    assert result.returncode == 1
    assert "linha" in result.stderr.lower()
    assert "coluna" in result.stderr.lower()