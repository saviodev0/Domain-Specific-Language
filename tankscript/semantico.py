from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from gerado.TankScriptParser import TankScriptParser
from gerado.TankScriptParserVisitor import TankScriptParserVisitor

from .arvore import arvore_sintatica
from .catalogo import ARMAS, ATRIBUTOS, MAXIMO_DE_ARMAS, UNIDADES

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
        tipo = ctx.getChild(0).getText()
        unidade = Unidade(tipo)
        self._rejeitar_propriedades(ctx.propriedade(), tipo, {atributo: UNIDADES[tipo][atributo] for atributo in ATRIBUTOS})

        permitidas = UNIDADES[tipo]["armas"]
        for arma in ctx.arma():
            nome_arma = arma.IDENTIFIER()
            tipo_arma = arma.getChild(0).getText()
            if tipo_arma not in permitidas:
                self._erro(arma, f"{tipo} não monta {tipo_arma}; use {', '.join(permitidas)}")
            elif nome_arma.getText() in unidade.armas:
                self._erro(nome_arma, f"arma '{nome_arma.getText()}' já declarada em '{nome.getText()}'")
            elif len(unidade.armas) == MAXIMO_DE_ARMAS:
                self._erro(nome_arma, f"'{nome.getText()}' já tem {MAXIMO_DE_ARMAS} armas, o máximo por unidade")
            else:
                unidade.armas[nome_arma.getText()] = tipo_arma
            self._rejeitar_propriedades(arma.propriedade(), tipo_arma, ARMAS[tipo_arma])

        if nome.getText() in self.unidades:
            self._erro(nome, f"unidade '{nome.getText()}' já declarada")
        else:
            self.unidades[nome.getText()] = unidade

    def _rejeitar_propriedades(self, propriedades, tipo: str, fixos: Dict[str, int]) -> None:
        for propriedade in propriedades:
            nome = propriedade.IDENTIFIER()
            texto = nome.getText()
            if texto in fixos:
                self._erro(nome, f"'{texto}' é fixo: todo {tipo} tem {texto} {fixos[texto]}; declare só o nome e as armas")
            else:
                self._erro(nome, f"'{texto}' não é atributo de {tipo}; os atributos vêm do tipo: {', '.join(fixos)}")

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
        self._verificar_alvo(atacante, alvo)

    def visitDisparo(self, ctx: TankScriptParser.DisparoContext):
        atacante, arma, alvo = ctx.IDENTIFIER()
        unidade = self._unidade(atacante)
        if unidade is not None and arma.getText() not in unidade.armas:
            self._erro(arma, f"'{atacante.getText()}' não possui a arma '{arma.getText()}'")
        self._unidade(alvo)
        self._verificar_alvo(atacante, alvo)

    def _verificar_alvo(self, atacante, alvo) -> None:
        if atacante.getText() == alvo.getText():
            self._erro(alvo, f"'{atacante.getText()}' não pode atacar a si mesmo")
            return
        equipe = self._equipe_da_unidade.get(atacante.getText())
        if equipe is not None and equipe == self._equipe_da_unidade.get(alvo.getText()):
            self._erro(alvo, f"'{alvo.getText()}' é da mesma equipe de '{atacante.getText()}' ({equipe})")

    def visitMergulho(self, ctx: TankScriptParser.MergulhoContext):
        self._exigir_submarino(ctx.DIVE(), ctx.IDENTIFIER())
        if float(ctx.numero().getText()) <= 0:
            self._erro(ctx.numero(), "a profundidade do 'dive' precisa ser maior que 0; para subir, use 'surface'")

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
