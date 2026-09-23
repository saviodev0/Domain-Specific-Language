import enum
from typing import List, Any

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
    REPEAT = "repeat"   # NOVO
    SONAR = "sonar"     # NOVO

    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"

    LBRACE = "{"
    RBRACE = "}"
    DOT = "."
    LESS = "<"
    GREATER = ">"
    EQ = "=="
    PLUS = "+"
    MINUS = "-"

    EOF = "EOF"

KEYWORDS = {
    "tank": TokenType.TANK,
    "submarine": TokenType.SUBMARINE,
    "gun": TokenType.GUN,
    "torpedo": TokenType.TORPEDO,
    "team": TokenType.TEAM,
    "battle": TokenType.BATTLE,
    "move": TokenType.MOVE,
    "attack": TokenType.ATTACK,
    "fire": TokenType.FIRE,
    "dive": TokenType.DIVE,
    "surface": TokenType.SURFACE,
    "if": TokenType.IF,
    "vs": TokenType.VS,
    "repeat": TokenType.REPEAT,
    "sonar": TokenType.SONAR,
}

class Token:
    def __init__(self, type: TokenType, value: Any, line: int):
        self.type = type
        self.value = value
        self.line = line

class Lexer:
    def __init__(self, code: str):
        self.code = code
        self.pos = 0
        self.line = 1

    def tokenize(self) -> List[Token]:
        tokens = []
        while self.pos < len(self.code):
            char = self.code[self.pos]

            # IGNERA COMENTÁRIOS QUE INICIAM COM '#'
            if char == "#":
                while self.pos < len(self.code) and self.code[self.pos] != "\n":
                    self.pos += 1
                continue

            if char in " \t\r":
                self.pos += 1
            elif char == "\n":
                self.line += 1
                self.pos += 1
            elif char == "{":
                tokens.append(Token(TokenType.LBRACE, "{", self.line))
                self.pos += 1
            elif char == "}":
                tokens.append(Token(TokenType.RBRACE, "}", self.line))
                self.pos += 1
            elif char == ".":
                tokens.append(Token(TokenType.DOT, ".", self.line))
                self.pos += 1
            elif char == "+":
                tokens.append(Token(TokenType.PLUS, "+", self.line))
                self.pos += 1
            elif char == "-":
                tokens.append(Token(TokenType.MINUS, "-", self.line))
                self.pos += 1
            elif char == "<":
                tokens.append(Token(TokenType.LESS, "<", self.line))
                self.pos += 1
            elif char == ">":
                tokens.append(Token(TokenType.GREATER, ">", self.line))
                self.pos += 1
            elif char == "=":
                if self.pos + 1 < len(self.code) and self.code[self.pos + 1] == "=":
                    tokens.append(Token(TokenType.EQ, "==", self.line))
                    self.pos += 2
                else:
                    raise SyntaxError(f"Caractere inválido '=' na linha {self.line}. Esperado '=='")
            elif char.isdigit():
                start = self.pos
                while self.pos < len(self.code) and self.code[self.pos].isdigit():
                    self.pos += 1
                value = int(self.code[start:self.pos])
                tokens.append(Token(TokenType.NUMBER, value, self.line))
            elif char.isalpha() or char == "_":
                start = self.pos
                while self.pos < len(self.code) and (self.code[self.pos].isalnum() or self.code[self.pos] == "_"):
                    self.pos += 1
                text = self.code[start:self.pos]
                token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
                tokens.append(Token(token_type, text, self.line))
            else:
                raise SyntaxError(f"Caractere inesperado '{char}' na linha {self.line}")


        tokens.append(Token(TokenType.EOF, None, self.line))
        return tokens
