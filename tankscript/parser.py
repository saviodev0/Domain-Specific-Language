from typing import Any, Dict, List

from .lexer import Token, TokenType


class Parser:
    DECLARATION_STARTS = (
        TokenType.TANK,
        TokenType.SUBMARINE,
        TokenType.TEAM,
        TokenType.BATTLE,
    )
    STATEMENT_STARTS = (
        TokenType.MOVE,
        TokenType.ATTACK,
        TokenType.FIRE,
        TokenType.DIVE,
        TokenType.SURFACE,
        TokenType.IF,
        TokenType.REPEAT,
        TokenType.SONAR,
    )
    COMPARISON_OPERATORS = (TokenType.LESS, TokenType.GREATER, TokenType.EQ)
    NUMERIC_TOKENS = (TokenType.NUMBER, TokenType.FLOAT)

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current_token(self) -> Token:
        if self.pos >= len(self.tokens):
            if self.tokens:
                previous = self.tokens[-1]
                raise SyntaxError(
                    f"Linha {previous.line}, coluna {previous.column}: "
                    "Fim inesperado da lista de tokens; esperado EOF"
                )
            raise SyntaxError("Linha 1, coluna 1: Lista de tokens vazia; esperado EOF")
        return self.tokens[self.pos]

    def consume(self, expected_type: TokenType) -> Token:
        token = self.current_token()
        if token.type is not expected_type:
            self._raise_expected(token, f"token {expected_type.name}")
        self.pos += 1
        return token

    def consume_numeric(self) -> int | float:
        token = self.current_token()
        if token.type not in self.NUMERIC_TOKENS:
            self._raise_expected(token, "número")
        self.pos += 1
        return token.value

    def match(self, *token_types: TokenType) -> bool:
        return self.current_token().type in token_types

    @staticmethod
    def _raise_expected(token: Token, expected: str) -> None:
        raise SyntaxError(
            f"Linha {token.line}, coluna {token.column}: Esperado {expected}, "
            f"mas obteve {token.type.name} ('{token.value}')"
        )

    @staticmethod
    def _raise_unexpected(token: Token, context: str) -> None:
        raise SyntaxError(
            f"Linha {token.line}, coluna {token.column}: "
            f"Token inesperado {token.type.name} ('{token.value}') {context}"
        )

    def parse(self) -> Dict[str, Any]:
        declarations = []
        statements = []

        while not self.match(TokenType.EOF):
            if self.match(*self.DECLARATION_STARTS):
                declarations.append(self.parse_declaration())
            elif self.match(*self.STATEMENT_STARTS):
                statements.append(self._parse_statement())
            else:
                self._raise_unexpected(self.current_token(), "no início do programa")

        self.consume(TokenType.EOF)
        return {
            "type": "Program",
            "declarations": declarations,
            "statements": statements,
        }

    def parse_declaration(self) -> Dict[str, Any]:
        token = self.current_token()
        if token.type is TokenType.TANK:
            return self.parse_unit_declaration("TankDeclaration")
        if token.type is TokenType.SUBMARINE:
            return self.parse_unit_declaration("SubmarineDeclaration")
        if token.type is TokenType.TEAM:
            return self.parse_team()
        if token.type is TokenType.BATTLE:
            return self.parse_battle()
        self._raise_unexpected(token, "no início de uma declaração")

    def parse_unit_declaration(self, decl_type: str) -> Dict[str, Any]:
        self.pos += 1
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.LBRACE)

        properties = {}
        weapons = []
        while not self.match(TokenType.RBRACE):
            if self.match(TokenType.EOF):
                self._raise_expected(self.current_token(), "RBRACE para fechar a declaração")
            if self.match(TokenType.GUN, TokenType.TORPEDO):
                weapons.append(self.parse_weapon())
            elif self.match(TokenType.IDENTIFIER):
                prop_name = self.consume(TokenType.IDENTIFIER).value
                prop_val = self.consume_numeric()
                properties[prop_name] = prop_val
            else:
                self._raise_unexpected(self.current_token(), "na declaração da unidade")

        self.consume(TokenType.RBRACE)
        return {
            "type": decl_type,
            "name": name,
            "properties": properties,
            "weapons": weapons,
        }

    def parse_weapon(self) -> Dict[str, Any]:
        weapon_type = self.current_token().value
        self.pos += 1
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.LBRACE)

        properties = {}
        while not self.match(TokenType.RBRACE):
            if self.match(TokenType.EOF):
                self._raise_expected(self.current_token(), "RBRACE para fechar a arma")
            prop_name = self.consume(TokenType.IDENTIFIER).value
            prop_val = self.consume_numeric()
            properties[prop_name] = prop_val

        self.consume(TokenType.RBRACE)
        return {
            "type": "WeaponDeclaration",
            "kind": weapon_type,
            "name": name,
            "properties": properties,
        }

    def parse_team(self) -> Dict[str, Any]:
        self.consume(TokenType.TEAM)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.LBRACE)

        members = []
        while not self.match(TokenType.RBRACE):
            if self.match(TokenType.EOF):
                self._raise_expected(self.current_token(), "RBRACE para fechar a equipe")
            members.append(self.consume(TokenType.IDENTIFIER).value)

        self.consume(TokenType.RBRACE)
        return {"type": "TeamDeclaration", "name": name, "members": members}

    def parse_battle(self) -> Dict[str, Any]:
        self.consume(TokenType.BATTLE)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.LBRACE)
        team1 = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.VS)
        team2 = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.RBRACE)
        return {
            "type": "BattleDeclaration",
            "name": name,
            "team1": team1,
            "team2": team2,
        }

    def parse_statement(self) -> Dict[str, Any]:
        statement = self._parse_statement()
        self.consume(TokenType.EOF)
        return statement

    def _parse_statement(self) -> Dict[str, Any]:
        token = self.current_token()
        if token.type is TokenType.MOVE:
            self.consume(TokenType.MOVE)
            unit = self.consume(TokenType.IDENTIFIER).value
            x = self.consume_numeric()
            y = self.consume_numeric()
            return {"type": "MoveStatement", "unit": unit, "x": x, "y": y}

        if token.type is TokenType.ATTACK:
            self.consume(TokenType.ATTACK)
            attacker = self.consume(TokenType.IDENTIFIER).value
            target = self.consume(TokenType.IDENTIFIER).value
            return {"type": "AttackStatement", "attacker": attacker, "target": target}

        if token.type is TokenType.FIRE:
            self.consume(TokenType.FIRE)
            attacker = self.consume(TokenType.IDENTIFIER).value
            weapon = self.consume(TokenType.IDENTIFIER).value
            target = self.consume(TokenType.IDENTIFIER).value
            return {
                "type": "FireStatement",
                "attacker": attacker,
                "weapon": weapon,
                "target": target,
            }

        if token.type is TokenType.DIVE:
            self.consume(TokenType.DIVE)
            unit = self.consume(TokenType.IDENTIFIER).value
            depth = self.consume_numeric()
            return {"type": "DiveStatement", "unit": unit, "depth": depth}

        if token.type is TokenType.SURFACE:
            self.consume(TokenType.SURFACE)
            unit = self.consume(TokenType.IDENTIFIER).value
            return {"type": "SurfaceStatement", "unit": unit}

        if token.type is TokenType.SONAR:
            self.consume(TokenType.SONAR)
            unit = self.consume(TokenType.IDENTIFIER).value
            return {"type": "SonarStatement", "unit": unit}

        if token.type is TokenType.IF:
            return self.parse_if()

        if token.type is TokenType.REPEAT:
            return self.parse_repeat()

        self._raise_unexpected(token, "no início de uma instrução")

    def parse_repeat(self) -> Dict[str, Any]:
        self.consume(TokenType.REPEAT)
        count = self.consume(TokenType.NUMBER).value
        self.consume(TokenType.LBRACE)
        body = self._parse_statement_block()
        return {"type": "RepeatStatement", "count": count, "body": body}

    def parse_if(self) -> Dict[str, Any]:
        self.consume(TokenType.IF)
        condition = self.parse_expression()
        self.consume(TokenType.LBRACE)
        body = self._parse_statement_block()
        return {"type": "IfStatement", "condition": condition, "body": body}

    def _parse_statement_block(self) -> List[Dict[str, Any]]:
        body = []
        while not self.match(TokenType.RBRACE):
            if self.match(TokenType.EOF):
                self._raise_expected(self.current_token(), "RBRACE para fechar o bloco")
            body.append(self._parse_statement())
        self.consume(TokenType.RBRACE)
        return body

    def parse_expression(self) -> Dict[str, Any]:
        left = self.parse_primary_expr()
        operator = self.current_token()
        if operator.type not in self.COMPARISON_OPERATORS:
            self._raise_expected(operator, "operador de comparação (<, > ou ==)")
        self.pos += 1
        right = self.parse_primary_expr()
        return {
            "type": "BinaryExpression",
            "operator": operator.value,
            "left": left,
            "right": right,
        }

    def parse_primary_expr(self) -> Dict[str, Any]:
        token = self.current_token()
        if token.type in (*self.NUMERIC_TOKENS, TokenType.STRING):
            self.pos += 1
            return {"type": "Literal", "value": token.value}

        if token.type is TokenType.IDENTIFIER:
            self.pos += 1
            if self.match(TokenType.DOT):
                self.consume(TokenType.DOT)
                prop = self.consume(TokenType.IDENTIFIER).value
                return {"type": "MemberAccess", "unit": token.value, "property": prop}
            return {"type": "Identifier", "name": token.value}

        self._raise_unexpected(token, "em uma expressão")
