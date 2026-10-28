import enum
from typing import Any, List

from antlr4 import InputStream
from antlr4.error.ErrorListener import ErrorListener

from gerado.TankScriptLexer import TankScriptLexer as GeneratedTankScriptLexer

class TokenType(enum.Enum):
    TANK = "tank"
    SUBMARINE = "submarine"
    GUN = "gun"
    TORPEDO = "torpedo"
    TEAM = "team"
    BATTLE = "battle"
    MOVE = "move"
    ATTACK = "attack"
    FIRE = "fire"
    DIVE = "dive"
    SURFACE = "surface"
    IF = "if"
    VS = "vs"
    REPEAT = "repeat"
    SONAR = "sonar"

    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    FLOAT = "FLOAT"
    STRING = "STRING"

    LBRACE = "{"
    RBRACE = "}"
    DOT = "."
    LESS = "<"
    GREATER = ">"
    EQ = "=="
    PLUS = "+"
    MINUS = "-"

    EOF = "EOF"

class Token:
    def __init__(self, type: TokenType, value: Any, line: int, column: int = 1):
        self.type = type
        self.value = value
        self.line = line
        self.column = column


class _LexerErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, error):
        character = ""
        if error is not None:
            character = recognizer.inputStream.getText(error.startIndex, error.startIndex)

        if character in ("'", '"'):
            message = f"Literal de texto não terminado na linha {line}, coluna {column + 1}"
        elif character == "=":
            message = f"Caractere inválido '=' na linha {line}, coluna {column + 1}. Esperado '=='"
        else:
            message = f"Caractere inesperado '{character}' na linha {line}, coluna {column + 1}"
        raise SyntaxError(message)


class Lexer:
    def __init__(self, code: str):
        self.code = code

    def tokenize(self) -> List[Token]:
        tokens = []
        lexer = GeneratedTankScriptLexer(InputStream(self.code))
        lexer.removeErrorListeners()
        lexer.addErrorListener(_LexerErrorListener())

        while True:
            antlr_token = lexer.nextToken()
            if antlr_token.type == -1:
                tokens.append(Token(TokenType.EOF, None, antlr_token.line, antlr_token.column + 1))
                break

            token_name = lexer.symbolicNames[antlr_token.type]
            if token_name == "MALFORMED_NUMBER":
                raise SyntaxError(
                    f"Número real malformado na linha {antlr_token.line}, "
                    f"coluna {antlr_token.column + 1}: {antlr_token.text}"
                )
            token_type = TokenType[token_name]
            value: Any = antlr_token.text
            if token_type is TokenType.NUMBER:
                value = int(value)
            elif token_type is TokenType.FLOAT:
                value = float(value)
            elif token_type is TokenType.STRING:
                value = value[1:-1]

            tokens.append(Token(token_type, value, antlr_token.line, antlr_token.column + 1))

        return tokens
