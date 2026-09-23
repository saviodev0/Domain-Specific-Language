from typing import List, Dict, Any
from .lexer import Token, TokenType

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current_token(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, expected_type: TokenType) -> Token:
        token = self.current_token()
        if token.type != expected_type:
            raise SyntaxError(f"Linha {token.line}: Esperado token {expected_type.name}, mas obteve {token.type.name} ('{token.value}')")
        self.pos += 1
        return token

    def match(self, *token_types: TokenType) -> bool:
        return self.current_token().type in token_types

    def parse(self) -> Dict[str, Any]:
        declarations = []
        statements = []

        while self.current_token().type != TokenType.EOF:
            if self.match(TokenType.TANK, TokenType.SUBMARINE, TokenType.TEAM, TokenType.BATTLE):
                declarations.append(self.parse_declaration())
            elif self.match(TokenType.MOVE, TokenType.ATTACK, TokenType.FIRE, TokenType.DIVE, TokenType.SURFACE, TokenType.IF, TokenType.REPEAT, TokenType.SONAR):
                statements.append(self.parse_statement())
            else:
                token = self.current_token()
                raise SyntaxError(f"Linha {token.line}: Declaração ou instrução inválida iniciando com '{token.value}'")

        return {
            "type": "Program",
            "declarations": declarations,
            "statements": statements
        }

    def parse_declaration(self) -> Dict[str, Any]:
        token = self.current_token()
        if token.type == TokenType.TANK:
            return self.parse_unit_declaration("TankDeclaration")
        elif token.type == TokenType.SUBMARINE:
            return self.parse_unit_declaration("SubmarineDeclaration")
        elif token.type == TokenType.TEAM:
            return self.parse_team()
        elif token.type == TokenType.BATTLE:
            return self.parse_battle()

    def parse_unit_declaration(self, decl_type: str) -> Dict[str, Any]:
        self.pos += 1
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.LBRACE)

        properties = {}
        weapons = []

        while not self.match(TokenType.RBRACE):
            if self.match(TokenType.GUN, TokenType.TORPEDO):
                weapons.append(self.parse_weapon())
            elif self.match(TokenType.IDENTIFIER):
                prop_name = self.consume(TokenType.IDENTIFIER).value
                prop_val = self.consume(TokenType.NUMBER).value
                properties[prop_name] = prop_val

        self.consume(TokenType.RBRACE)
        return {
            "type": decl_type,
            "name": name,
            "properties": properties,
            "weapons": weapons
        }

    def parse_weapon(self) -> Dict[str, Any]:
        weapon_type = self.current_token().value
        self.pos += 1
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.LBRACE)

        properties = {}
        while not self.match(TokenType.RBRACE):
            prop_name = self.consume(TokenType.IDENTIFIER).value
            prop_val = self.consume(TokenType.NUMBER).value
            properties[prop_name] = prop_val

        self.consume(TokenType.RBRACE)
        return {
            "type": "WeaponDeclaration",
            "kind": weapon_type,
            "name": name,
            "properties": properties
        }

    def parse_team(self) -> Dict[str, Any]:
        self.consume(TokenType.TEAM)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.LBRACE)

        members = []
        while not self.match(TokenType.RBRACE):
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
        return {"type": "BattleDeclaration", "name": name, "team1": team1, "team2": team2}

    def parse_statement(self) -> Dict[str, Any]:
        token = self.current_token()
        if token.type == TokenType.MOVE:
            self.consume(TokenType.MOVE)
            unit = self.consume(TokenType.IDENTIFIER).value
            x = self.consume(TokenType.NUMBER).value
            y = self.consume(TokenType.NUMBER).value
            return {"type": "MoveStatement", "unit": unit, "x": x, "y": y}

        elif token.type == TokenType.ATTACK:
            self.consume(TokenType.ATTACK)
            attacker = self.consume(TokenType.IDENTIFIER).value
            target = self.consume(TokenType.IDENTIFIER).value
            return {"type": "AttackStatement", "attacker": attacker, "target": target}

        elif token.type == TokenType.FIRE:
            self.consume(TokenType.FIRE)
            attacker = self.consume(TokenType.IDENTIFIER).value
            weapon = self.consume(TokenType.IDENTIFIER).value
            target = self.consume(TokenType.IDENTIFIER).value
            return {"type": "FireStatement", "attacker": attacker, "weapon": weapon, "target": target}

        elif token.type == TokenType.DIVE:
            self.consume(TokenType.DIVE)
            unit = self.consume(TokenType.IDENTIFIER).value
            depth = self.consume(TokenType.NUMBER).value
            return {"type": "DiveStatement", "unit": unit, "depth": depth}

        elif token.type == TokenType.SURFACE:
            self.consume(TokenType.SURFACE)
            unit = self.consume(TokenType.IDENTIFIER).value
            return {"type": "SurfaceStatement", "unit": unit}

        elif token.type == TokenType.SONAR:
            self.consume(TokenType.SONAR)
            unit = self.consume(TokenType.IDENTIFIER).value
            return {"type": "SonarStatement", "unit": unit}

        elif token.type == TokenType.IF:
            return self.parse_if()

        elif token.type == TokenType.REPEAT:
            return self.parse_repeat()

    def parse_repeat(self) -> Dict[str, Any]:
        self.consume(TokenType.REPEAT)
        count = self.consume(TokenType.NUMBER).value
        self.consume(TokenType.LBRACE)

        body = []
        while not self.match(TokenType.RBRACE):
            body.append(self.parse_statement())

        self.consume(TokenType.RBRACE)
        return {"type": "RepeatStatement", "count": count, "body": body}

    def parse_if(self) -> Dict[str, Any]:
        self.consume(TokenType.IF)
        condition = self.parse_expression()
        self.consume(TokenType.LBRACE)

        body = []
        while not self.match(TokenType.RBRACE):
            body.append(self.parse_statement())

        self.consume(TokenType.RBRACE)
        return {"type": "IfStatement", "condition": condition, "body": body}

    def parse_expression(self) -> Dict[str, Any]:
        left = self.parse_primary_expr()
        if self.match(TokenType.LESS, TokenType.GREATER, TokenType.EQ):
            op = self.current_token().value
            self.pos += 1
            right = self.parse_primary_expr()
            return {"type": "BinaryExpression", "operator": op, "left": left, "right": right}
        return left

    def parse_primary_expr(self) -> Dict[str, Any]:
        token = self.current_token()
        if token.type == TokenType.NUMBER:
            self.pos += 1
            return {"type": "Literal", "value": token.value}
        elif token.type == TokenType.IDENTIFIER:
            unit = token.value
            self.pos += 1
            if self.match(TokenType.DOT):
                self.consume(TokenType.DOT)
                prop = self.consume(TokenType.IDENTIFIER).value
                return {"type": "MemberAccess", "unit": unit, "property": prop}
            return {"type": "Identifier", "name": unit}
        raise SyntaxError(f"Linha {token.line}: Expressão inválida com '{token.value}'")