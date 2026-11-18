from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from antlr4.tree.Trees import Trees

from gerado.TankScriptLexer import TankScriptLexer
from gerado.TankScriptParser import TankScriptParser

from .lexer import Lexer


COMANDOS = {
    TankScriptParser.MOVE, TankScriptParser.ATTACK, TankScriptParser.FIRE,
    TankScriptParser.DIVE, TankScriptParser.SURFACE, TankScriptParser.SONAR,
}
TIPOS_DE_ARMA = {TankScriptParser.GUN, TankScriptParser.TORPEDO, TankScriptParser.MISSILE}
NOME_DE_EXEMPLO = {TankScriptParser.GUN: "Canhao", TankScriptParser.TORPEDO: "Dardo", TankScriptParser.MISSILE: "Ferrao"}


def _mensagem_para_engano_comum(tokens, encontrado) -> str | None:
    """Reescreve a mensagem do ANTLR para os dois enganos mais comuns de quem está começando."""
    tokens.fill()
    indice = encontrado.tokenIndex
    anterior = tokens.get(indice - 1) if indice >= 1 else None
    antes_do_anterior = tokens.get(indice - 2) if indice >= 2 else None
    seguinte = tokens.get(indice + 1) if indice + 1 < len(tokens.tokens) else None

    if encontrado.type == TankScriptParser.IDENTIFIER and seguinte is not None and seguinte.type in COMANDOS:
        return (f"o comando vem antes da unidade: escreva '{seguinte.text} {encontrado.text} ...' "
                f"em vez de '{encontrado.text} {seguinte.text} ...'")
    if (encontrado.type in TIPOS_DE_ARMA and antes_do_anterior is not None
            and antes_do_anterior.type == TankScriptParser.FIRE and anterior.type == TankScriptParser.IDENTIFIER):
        return (f"'{encontrado.text}' é o tipo da arma; o fire pede o nome dela, que vem depois do tipo "
                f"na declaração (em '{encontrado.text} {NOME_DE_EXEMPLO[encontrado.type]}', "
                f"o nome é {NOME_DE_EXEMPLO[encontrado.type]}). "
                f"Se preferir, use 'attack {anterior.text} alvo', que dispara a primeira arma pronta")
    return None


class _ParserErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, error):
        amigavel = None
        if offendingSymbol is not None:
            amigavel = _mensagem_para_engano_comum(recognizer.getTokenStream(), offendingSymbol)
        raise SyntaxError(f"Linha {line}, coluna {column + 1}: {amigavel or msg}")


def arvore_sintatica(source: str) -> TankScriptParser.ProgramaContext:
    Lexer(source).tokenize()

    tokens = CommonTokenStream(TankScriptLexer(InputStream(source)))
    parser = TankScriptParser(tokens)
    parser.removeErrorListeners()
    parser.addErrorListener(_ParserErrorListener())
    return parser.programa()


def arvore_como_texto(source: str) -> str:
    arvore = arvore_sintatica(source)
    return Trees.toStringTree(arvore, recog=arvore.parser)
