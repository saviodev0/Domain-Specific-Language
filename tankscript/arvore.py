from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from antlr4.tree.Trees import Trees

from gerado.TankScriptLexer import TankScriptLexer
from gerado.TankScriptParser import TankScriptParser

from .lexer import Lexer


class _ParserErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, error):
        raise SyntaxError(f"Linha {line}, coluna {column + 1}: {msg}")


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
