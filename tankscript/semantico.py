from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from gerado.TankScriptParser import TankScriptParser
from gerado.TankScriptParserVisitor import TankScriptParserVisitor

from .arvore import arvore_sintatica

PROPRIEDADES_DE_UNIDADE = {
    "tank": {"hp", "armor", "speed", "radar"},
    "submarine": {"hp", "armor", "speed", "radar", "depth"},
}
PROPRIEDADES_DE_ARMA = {"damage", "range", "ammo", "cooldown"}
PROPRIEDADES_INTEIRAS = {"hp", "armor", "speed", "damage", "range", "ammo", "cooldown"}
PROPRIEDADES_CONSULTAVEIS = {"hp", "armor", "speed", "radar", "depth", "x", "y"}

NUMERO = "número"
TEXTO = "texto"


class ErroSemantico(Exception):
    def __init__(self, erros: List[str]):
        self.erros = erros
        super().__init__("\n".join(erros))


@dataclass
class Unidade:
    tipo: str
    armas: Dict[str, str] = field(default_factory=dict)


class AnalisadorSemantico(TankScriptParserVisitor):
    def __init__(self):
        self.unidades: Dict[str, Unidade] = {}
        self.equipes: Dict[str, List[str]] = {}
        self.batalhas: Set[str] = set()
        self._equipe_da_unidade: Dict[str, str] = {}
        self._erros: List[Tuple[int, int, str]] = []

    @property
    def erros(self) -> List[str]:
        return [f"Linha {linha}, coluna {coluna}: {mensagem}" for linha, coluna, mensagem in sorted(self._erros)]

    def _erro(self, no, mensagem: str) -> None:
        token = no.symbol if hasattr(no, "symbol") else no.start
        self._erros.append((token.line, token.column + 1, mensagem))

    def visitPrograma(self, ctx: TankScriptParser.ProgramaContext):
        declaracoes = [declaracao.getChild(0) for declaracao in ctx.declaracao()]
        for tipo in (TankScriptParser.UnidadeContext, TankScriptParser.EquipeContext, TankScriptParser.BatalhaContext):
            for declaracao in declaracoes:
                if isinstance(declaracao, tipo):
                    self.visit(declaracao)
        for instrucao in ctx.instrucao():
            self.visit(instrucao)

    def visitUnidade(self, ctx: TankScriptParser.UnidadeContext):
        nome = ctx.IDENTIFIER()
        tipo = "tank" if ctx.TANK() else "submarine"
        unidade = Unidade(tipo)
        self._verificar_propriedades(ctx.propriedade(), PROPRIEDADES_DE_UNIDADE[tipo], f"{tipo} '{nome.getText()}'")

        for arma in ctx.arma():
            nome_arma = arma.IDENTIFIER()
            tipo_arma = "gun" if arma.GUN() else "torpedo"
            if nome_arma.getText() in unidade.armas:
                self._erro(nome_arma, f"arma '{nome_arma.getText()}' já declarada em '{nome.getText()}'")
            else:
                unidade.armas[nome_arma.getText()] = tipo_arma
            self._verificar_propriedades(
                arma.propriedade(), PROPRIEDADES_DE_ARMA, f"{tipo_arma} '{nome_arma.getText()}'"
            )

        if nome.getText() in self.unidades:
            self._erro(nome, f"unidade '{nome.getText()}' já declarada")
        else:
            self.unidades[nome.getText()] = unidade

    def _verificar_propriedades(self, propriedades, permitidas: Set[str], dono: str) -> None:
        vistas = set()
        for propriedade in propriedades:
            nome = propriedade.IDENTIFIER()
            texto = nome.getText()
            if texto not in permitidas:
                self._erro(nome, f"propriedade '{texto}' não existe em {dono}; use: {', '.join(sorted(permitidas))}")
                continue
            if texto in vistas:
                self._erro(nome, f"propriedade '{texto}' repetida em {dono}")
            vistas.add(texto)
            valor = propriedade.numero()
            if texto in PROPRIEDADES_INTEIRAS and valor.FLOAT():
                self._erro(valor, f"'{texto}' deve ser inteiro, mas recebeu {valor.getText()}")

    def visitEquipe(self, ctx: TankScriptParser.EquipeContext):
        nome, *membros = ctx.IDENTIFIER()
        vistos = set()
        for membro in membros:
            texto = membro.getText()
            if texto not in self.unidades:
                self._erro(membro, f"unidade '{texto}' não declarada")
            elif texto in vistos:
                self._erro(membro, f"unidade '{texto}' repetida na equipe '{nome.getText()}'")
            elif texto in self._equipe_da_unidade:
                self._erro(membro, f"unidade '{texto}' já pertence à equipe '{self._equipe_da_unidade[texto]}'")
            else:
                self._equipe_da_unidade[texto] = nome.getText()
            vistos.add(texto)

        if nome.getText() in self.equipes:
            self._erro(nome, f"equipe '{nome.getText()}' já declarada")
        else:
            self.equipes[nome.getText()] = [membro.getText() for membro in membros]

    def visitBatalha(self, ctx: TankScriptParser.BatalhaContext):
        nome, equipe1, equipe2 = ctx.IDENTIFIER()
        if nome.getText() in self.batalhas:
            self._erro(nome, f"batalha '{nome.getText()}' já declarada")
        self.batalhas.add(nome.getText())
        for equipe in (equipe1, equipe2):
            if equipe.getText() not in self.equipes:
                self._erro(equipe, f"equipe '{equipe.getText()}' não declarada")
        if equipe1.getText() == equipe2.getText():
            self._erro(equipe2, f"a equipe '{equipe1.getText()}' não pode enfrentar a si mesma")

    def _unidade(self, no) -> Optional[Unidade]:
        unidade = self.unidades.get(no.getText())
        if unidade is None:
            self._erro(no, f"unidade '{no.getText()}' não declarada")
        return unidade

    def visitMovimento(self, ctx: TankScriptParser.MovimentoContext):
        self._unidade(ctx.IDENTIFIER())

    def visitAtaque(self, ctx: TankScriptParser.AtaqueContext):
        atacante, alvo = ctx.IDENTIFIER()
        unidade = self._unidade(atacante)
        self._unidade(alvo)
        if unidade is not None and not unidade.armas:
            self._erro(atacante, f"'{atacante.getText()}' não tem armas para atacar")

    def visitDisparo(self, ctx: TankScriptParser.DisparoContext):
        atacante, arma, alvo = ctx.IDENTIFIER()
        unidade = self._unidade(atacante)
        if unidade is not None and arma.getText() not in unidade.armas:
            self._erro(arma, f"'{atacante.getText()}' não possui a arma '{arma.getText()}'")
        self._unidade(alvo)

    def visitMergulho(self, ctx: TankScriptParser.MergulhoContext):
        self._exigir_submarino(ctx.DIVE(), ctx.IDENTIFIER())

    def visitEmersao(self, ctx: TankScriptParser.EmersaoContext):
        self._exigir_submarino(ctx.SURFACE(), ctx.IDENTIFIER())

    def _exigir_submarino(self, comando, nome) -> None:
        unidade = self._unidade(nome)
        if unidade is not None and unidade.tipo != "submarine":
            self._erro(nome, f"'{comando.getText()}' só vale para submarinos, e '{nome.getText()}' é {unidade.tipo}")

    def visitSonar(self, ctx: TankScriptParser.SonarContext):
        self._unidade(ctx.IDENTIFIER())

    def visitComparacao(self, ctx: TankScriptParser.ComparacaoContext):
        esquerda, direita = (self._tipo(primario) for primario in ctx.primario())
        operador = ctx.getChild(1)
        if esquerda is None or direita is None:
            return
        if operador.getText() in ("<", ">") and (esquerda, direita) != (NUMERO, NUMERO):
            self._erro(operador, f"'{operador.getText()}' compara números, mas recebeu {esquerda} e {direita}")
        elif esquerda != direita:
            self._erro(operador, f"'==' compara valores do mesmo tipo, mas recebeu {esquerda} e {direita}")

    def _tipo(self, ctx: TankScriptParser.PrimarioContext) -> Optional[str]:
        if ctx.numero():
            return NUMERO
        if ctx.STRING():
            return TEXTO
        identificadores = ctx.IDENTIFIER()
        if len(identificadores) == 1:
            nome = identificadores[0].getText()
            self._erro(ctx, f"'{nome}' sozinho não tem valor; use unidade.propriedade, como {nome}.hp")
            return None
        unidade, propriedade = identificadores
        if self._unidade(unidade) is None:
            return None
        if propriedade.getText() not in PROPRIEDADES_CONSULTAVEIS:
            self._erro(
                propriedade,
                f"propriedade '{propriedade.getText()}' não pode ser consultada; "
                f"use: {', '.join(sorted(PROPRIEDADES_CONSULTAVEIS))}",
            )
            return None
        return NUMERO


def analisar(source: str) -> AnalisadorSemantico:
    analisador = AnalisadorSemantico()
    analisador.visit(arvore_sintatica(source))
    if analisador.erros:
        raise ErroSemantico(analisador.erros)
    return analisador
