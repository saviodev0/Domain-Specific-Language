import pytest

from tankscript.lexer import Lexer, TokenType


def tokenize(source):
    return Lexer(source).tokenize()


def test_all_keywords_are_recognized_before_identifiers():
    expected = [
        TokenType.TANK,
        TokenType.SUBMARINE,
        TokenType.GUN,
        TokenType.TORPEDO,
        TokenType.TEAM,
        TokenType.BATTLE,
        TokenType.MOVE,
        TokenType.ATTACK,
        TokenType.FIRE,
        TokenType.DIVE,
        TokenType.SURFACE,
        TokenType.IF,
        TokenType.VS,
        TokenType.REPEAT,
        TokenType.SONAR,
    ]

    assert [token.type for token in tokenize(
        "tank submarine gun torpedo team battle move attack fire dive surface if vs repeat sonar"
    )[:-1]] == expected


@pytest.mark.parametrize("source", ["tank1", "surfaceX", "_unit", "unit_9"])
def test_keyword_prefixes_and_identifier_shapes_remain_identifiers(source):
    token = tokenize(source)[0]

    assert token.type is TokenType.IDENTIFIER
    assert token.value == source


@pytest.mark.parametrize(
    ("source", "token_type", "value"),
    [
        ("0", TokenType.NUMBER, 0),
        ("00042", TokenType.NUMBER, 42),
        ("3.14", TokenType.FLOAT, 3.14),
        ("0.0", TokenType.FLOAT, 0.0),
        ("123456789012345678901234567890", TokenType.NUMBER, 123456789012345678901234567890),
    ],
)
def test_integer_and_float_tokens(source, token_type, value):
    token = tokenize(source)[0]

    assert token.type is token_type
    assert token.value == value


@pytest.mark.parametrize("source, expected", [("\"345\"", "345"), ("'text'", "text"), ("\"a\\\"b\"", "a\\\"b")])
def test_quoted_string_literals(source, expected):
    token = tokenize(source)[0]

    assert token.type is TokenType.STRING
    assert token.value == expected


@pytest.mark.parametrize("source", ["3.", ".14"])
def test_decimal_requires_digits_on_both_sides(source):
    tokens = tokenize(source)

    assert [token.type for token in tokens[:-1]] == (
        [TokenType.NUMBER, TokenType.DOT] if source == "3." else [TokenType.DOT, TokenType.NUMBER]
    )


def test_operators_braces_and_member_access():
    tokens = tokenize("{ } . < > == + -")

    assert [token.type for token in tokens[:-1]] == [
        TokenType.LBRACE,
        TokenType.RBRACE,
        TokenType.DOT,
        TokenType.LESS,
        TokenType.GREATER,
        TokenType.EQ,
        TokenType.PLUS,
        TokenType.MINUS,
    ]


def test_comments_are_skipped_and_line_tracking_continues():
    tokens = tokenize("tank # comment\nmove Unit 1 2")

    assert [token.type for token in tokens] == [TokenType.TANK, TokenType.MOVE, TokenType.IDENTIFIER,
                                               TokenType.NUMBER, TokenType.NUMBER, TokenType.EOF]
    assert tokens[1].line == 2
    assert tokens[1].column == 1


def test_token_columns_are_one_based():
    tokens = tokenize("  move Unit")

    assert (tokens[0].line, tokens[0].column) == (1, 3)
    assert (tokens[1].line, tokens[1].column) == (1, 8)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("=", "Caractere inválido '=' na linha 1, coluna 1"),
        ("\n  @", "Caractere inesperado '@' na linha 2, coluna 3"),
        ('\"unterminated', "Literal de texto não terminado na linha 1, coluna 1"),
        ('\"line\nbreak\"', "Literal de texto não terminado na linha 1, coluna 1"),
        ("\"escaped\\\nline\"", "Literal de texto não terminado na linha 1, coluna 1"),
    ],
)
def test_invalid_input_reports_line_and_column(source, message):
    with pytest.raises(SyntaxError, match=message):
        tokenize(source)