import io
import math
import random
import re
from contextlib import redirect_stdout
from typing import Any, Dict, List, Optional, Set

from gerado.TankScriptParser import TankScriptParser

from .ai import EnemyAI
from .arvore import arvore_sintatica
from .catalogo import CUSTO_DE_ARMA_EXTRA, MAXIMO_DE_ARMAS, ORCAMENTO, UNIDADES, custo
from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser
from .renderer import GridRenderer
from .semantico import AnalisadorSemantico, ErroSemantico

LIMITE_DE_INSTRUCOES = 500

_POSICAO = re.compile(r"[Ll]inha (\d+), coluna (\d+)")


class ErroDaPartida(Exception):
    pass


class LimiteDeExecucao(Exception):
    pass


def erros_do_programa(erro: Exception) -> List[Dict[str, Any]]:
    """Converte um erro léxico, sintático ou semântico em itens com linha e coluna."""
    if isinstance(erro, ErroSemantico):
        mensagens, fase = erro.erros, "semântico"
    else:
        mensagens, fase = [str(erro)], "sintático"
    itens = []
    for mensagem in mensagens:
        posicao = _POSICAO.search(mensagem)
        itens.append({
            "fase": fase,
            "linha": int(posicao.group(1)) if posicao else None,
            "coluna": int(posicao.group(2)) if posicao else None,
            "mensagem": mensagem,
        })
    return itens


class AnalisadorDaPartida(AnalisadorSemantico):
    """Análise semântica da E4 com as regras extras do jogo: limites do mapa e, nos turnos,
    apenas comandos para as unidades do jogador."""

    def __init__(self, renderer: GridRenderer, base: Optional[AnalisadorSemantico] = None,
                 comandaveis: Optional[Set[str]] = None):
        super().__init__()
        self._limites = (renderer.width * 10, renderer.height * 10)
        self._turno = base is not None
        self._comandaveis = comandaveis
        if base is not None:
            self.unidades = dict(base.unidades)
            self.equipes = dict(base.equipes)
            self.batalhas = set(base.batalhas)
            self._equipe_da_unidade = dict(base._equipe_da_unidade)

    def visitPrograma(self, ctx: TankScriptParser.ProgramaContext):
        if not self._turno:
            return super().visitPrograma(ctx)
        for declaracao in ctx.declaracao():
            self._erro(declaracao, "declarações ficam no cenário; no turno use apenas comandos")
        for instrucao in ctx.instrucao():
            self.visit(instrucao)

    def visitInstrucao(self, ctx: TankScriptParser.InstrucaoContext):
        comando = ctx.getChild(0)
        if self._comandaveis is not None and not isinstance(
            comando, (TankScriptParser.CondicionalContext, TankScriptParser.RepeticaoContext)
        ):
            ator = comando.getChild(1)
            if ator.getText() in self.unidades and ator.getText() not in self._comandaveis:
                self._erro(
                    ator,
                    f"'{ator.getText()}' não é da sua equipe; você comanda: {', '.join(sorted(self._comandaveis))}",
                )
        return self.visitChildren(ctx)

    def visitMovimento(self, ctx: TankScriptParser.MovimentoContext):
        super().visitMovimento(ctx)
        for eixo, numero, limite in zip("xy", ctx.numero(), self._limites):
            if not 0 <= float(numero.getText()) < limite:
                self._erro(numero, f"{eixo} = {numero.getText()} está fora do mapa (de 0 a {limite - 1})")


class AnalisadorDoExercito(AnalisadorDaPartida):
    """No modo arena o cenário só monta o exército do jogador: unidades e armas, dentro do orçamento."""

    def __init__(self, renderer: GridRenderer):
        super().__init__(renderer)
        self.declaradas: List[TankScriptParser.UnidadeContext] = []

    def visitPrograma(self, ctx: TankScriptParser.ProgramaContext):
        for declaracao in ctx.declaracao():
            if declaracao.unidade() is None:
                self._erro(declaracao, "na arena você só declara unidades; o jogo monta as equipes e a batalha")
        for instrucao in ctx.instrucao():
            self._erro(instrucao, "o cenário só monta o exército; as ordens ficam no turno.tank")
        for declaracao in ctx.declaracao():
            if declaracao.unidade() is not None:
                self.visit(declaracao.unidade())

        if not self.declaradas and not self._erros:
            self._erro(ctx, "declare pelo menos uma unidade, por exemplo: tank Rex { gun Canhao }")
        total = 0
        for unidade in self.declaradas:
            total += custo(unidade.getChild(0).getText(), len(unidade.arma()))
            if total > ORCAMENTO:
                self._erro(unidade, f"orçamento estourado: o exército chega a {total} de {ORCAMENTO} pontos")
                break

    def visitUnidade(self, ctx: TankScriptParser.UnidadeContext):
        super().visitUnidade(ctx)
        self.declaradas.append(ctx)

    def resumo(self) -> Dict[str, Any]:
        unidades = [
            {
                "nome": unidade.IDENTIFIER().getText(),
                "tipo": unidade.getChild(0).getText(),
                "armas": [arma.getChild(0).getText() for arma in unidade.arma()],
                "custo": custo(unidade.getChild(0).getText(), len(unidade.arma())),
            }
            for unidade in self.declaradas
        ]
        return {"unidades": unidades, "custo": sum(unidade["custo"] for unidade in unidades), "orcamento": ORCAMENTO}


def descrever_mapa(renderer: GridRenderer) -> Dict[str, Any]:
    return {
        "largura": renderer.width,
        "altura": renderer.height,
        "terreno": ["".join(celula.strip() for celula in linha) for linha in renderer.terrain],
    }


def _verificar(codigo: str, analisador: AnalisadorDaPartida) -> AnalisadorDaPartida:
    analisador.visit(arvore_sintatica(codigo))
    if analisador.erros:
        raise ErroSemantico(analisador.erros)
    return analisador


class _ParserComLinhas(Parser):
    def _parse_statement(self) -> Dict[str, Any]:
        linha = self.current_token().line
        instrucao = super()._parse_statement()
        instrucao["linha"] = linha
        return instrucao


def _ast(codigo: str) -> Dict[str, Any]:
    return _ParserComLinhas(Lexer(codigo).tokenize()).parse()


class _InterpretadorComEventos(Interpreter):
    """Registra um evento, com as mensagens e o estado do jogo, a cada instrução executada."""

    def __init__(self, ast: Dict[str, Any], partida: "Partida"):
        super().__init__(ast, renderer=partida.renderer)
        self._partida = partida
        self.iniciar("cenario")

    def iniciar(self, origem: str) -> None:
        self.origem = origem
        self.eventos: List[Dict[str, Any]] = []
        self._executadas = 0

    def registrar(self, tipo: str, saida: str = "", linha: Optional[int] = None, **dados) -> None:
        self.eventos.append({
            "tipo": tipo,
            "origem": self.origem,
            "linha": linha,
            "mensagens": [mensagem.strip() for mensagem in saida.splitlines() if mensagem.strip()],
            "estado": self._partida.estado(),
            **dados,
        })

    def execute_statement(self, stmt: Dict[str, Any]):
        self._executadas += 1
        if self._executadas > LIMITE_DE_INSTRUCOES:
            raise LimiteDeExecucao(
                f"Limite de {LIMITE_DE_INSTRUCOES} instruções por execução atingido; o restante foi ignorado"
            )

        if stmt["type"] == "IfStatement":
            self.registrar("IfStatement", linha=stmt.get("linha"), resultado=self.evaluate_expression(stmt["condition"]))
            return super().execute_statement(stmt)
        if stmt["type"] == "RepeatStatement":
            self.registrar("RepeatStatement", linha=stmt.get("linha"), vezes=stmt["count"])
            return super().execute_statement(stmt)

        saida = io.StringIO()
        with redirect_stdout(saida):
            super().execute_statement(stmt)
        dados = {chave: valor for chave, valor in stmt.items() if chave not in ("type", "linha")}
        self.registrar(stmt["type"], saida.getvalue(), stmt.get("linha"), instrucao=dados)


class Partida:
    """Uma partida jogada por turnos: o cenário declara as unidades e cada turno é um programa
    TankScript com as ordens do jogador, seguido da jogada da IA."""

    def __init__(self, codigo: str):
        self.renderer = GridRenderer()
        self.tabela = _verificar(codigo, AnalisadorDaPartida(self.renderer))
        ast = _ast(codigo)
        self.interpretador = _InterpretadorComEventos(ast, self)
        for declaracao in ast["declarations"]:
            self.interpretador.execute_declaration(declaracao)

        self.jogador, self.inimigo = self._lados()
        self.ia = EnemyAI(team_name=self.inimigo) if self.inimigo else None
        self.turno = 0
        self.estado_inicial = self.estado()
        self.eventos_do_cenario = self._executar(ast["statements"], "cenario")

    def _lados(self):
        batalhas = self.interpretador.battles
        if batalhas:
            return batalhas[0]["team1"], batalhas[0]["team2"]
        equipes = list(self.interpretador.teams)
        return (equipes + [None, None])[:2]

    def membros(self, equipe: Optional[str]) -> List[str]:
        return [nome for nome in self.interpretador.teams.get(equipe, []) if nome in self.interpretador.units]

    @property
    def comandaveis(self) -> List[str]:
        if self.jogador is None:
            return list(self.interpretador.units)
        return self.membros(self.jogador)

    @property
    def vencedor(self) -> Optional[str]:
        if self.jogador is None or self.inimigo is None:
            return None
        unidades = self.interpretador.units
        if not any(unidades[nome].is_alive() for nome in self.membros(self.jogador)):
            return self.inimigo
        if not any(unidades[nome].is_alive() for nome in self.membros(self.inimigo)):
            return self.jogador
        return None

    def _lado(self, nome: str) -> str:
        if nome in self.comandaveis:
            return "jogador"
        if nome in self.membros(self.inimigo):
            return "inimigo"
        return "neutro"

    def estado(self) -> Dict[str, Any]:
        unidades = self.interpretador.units
        comandaveis = self.comandaveis
        visiveis = self.renderer.visible_cells(unidades, comandaveis)
        if self.jogador is None:
            visiveis = {(x, y) for x in range(self.renderer.width) for y in range(self.renderer.height)}
        return {
            "unidades": [
                {
                    "nome": unidade.name,
                    "tipo": unidade.kind,
                    "lado": self._lado(unidade.name),
                    "x": unidade.x,
                    "y": unidade.y,
                    "hp": unidade.hp,
                    "hp_max": unidade.max_hp,
                    "armadura": unidade.armor,
                    "radar": unidade.radar_range,
                    "sonar": unidade.sonar_range,
                    "sonar_recarga": unidade.sonar_cooldown,
                    "velocidade": unidade.speed,
                    "movimento": unidade.speed if math.isinf(unidade.movement_left) else round(unidade.movement_left),
                    "profundidade": unidade.depth,
                    "exposto": unidade.exposed,
                    "detectado": unidade.sonar_ping_turns > 0,
                    "vivo": unidade.is_alive(),
                    "visivel": unidade.name in comandaveis or self.renderer.is_shown(unidade, False, visiveis),
                    "armas": [
                        {
                            "nome": arma["name"],
                            "tipo": arma["kind"],
                            "dano": arma["properties"].get("damage", 0),
                            "alcance": arma["properties"].get("range", 0),
                            "municao": arma["ammo"],
                            "recarga": arma["cooldown"],
                        }
                        for arma in unidade.weapons
                    ],
                }
                for unidade in unidades.values()
            ],
            "visiveis": sorted([x, y] for x, y in visiveis),
        }

    def mapa(self) -> Dict[str, Any]:
        return descrever_mapa(self.renderer)

    def _executar(self, instrucoes: List[Dict[str, Any]], origem: str) -> List[Dict[str, Any]]:
        self.interpretador.iniciar(origem)
        try:
            for instrucao in instrucoes:
                self.interpretador.execute_statement(instrucao)
        except LimiteDeExecucao as aviso:
            self.interpretador.registrar("Aviso", str(aviso))
        return self.interpretador.eventos

    def jogar_turno(self, codigo: str) -> List[Dict[str, Any]]:
        if self.vencedor is not None:
            raise ErroDaPartida(f"A partida terminou; a equipe '{self.vencedor}' venceu")
        _verificar(codigo, AnalisadorDaPartida(self.renderer, base=self.tabela, comandaveis=set(self.comandaveis)))
        ast = _ast(codigo)
        self.turno += 1

        self.interpretador.iniciar("sistema")
        saida = io.StringIO()
        with redirect_stdout(saida):
            self.interpretador.tick_cooldowns_and_effects()
        self.interpretador.registrar("InicioDoTurno", saida.getvalue(), turno=self.turno)
        eventos = self.interpretador.eventos

        eventos += self._executar(ast["statements"], "jogador")
        if self.ia is not None and self.vencedor is None:
            self.interpretador.iniciar("ia")
            self.ia.compute_turn(self.interpretador, self.membros(self.jogador))
            eventos += self.interpretador.eventos
        return eventos

    def resumo(self) -> Dict[str, Any]:
        return {
            "jogador": self.jogador,
            "inimigo": self.inimigo,
            "comandaveis": self.comandaveis,
            "turno": self.turno,
            "vencedor": self.vencedor,
        }


NOMES_INIMIGOS = {
    "tank": ("Brutus", "Rochedo", "Bastiao"),
    "submarine": ("Kraken", "Leviata", "Abissal"),
    "aircraft": ("Harpia", "Corvo", "Vespa"),
}
NOMES_DE_ARMAS = {"gun": "Canhao", "torpedo": "Torpedo", "missile": "Missil"}
COLUNA_DO_JOGADOR = 10
COLUNA_DO_INIMIGO = 180


def verificar_exercito(codigo: str) -> Dict[str, Any]:
    """Confere o exército do jogador sem iniciar a partida; usado pelo editor enquanto ele digita."""
    analisador = AnalisadorDoExercito(GridRenderer())
    try:
        analisador.visit(arvore_sintatica(codigo))
    except SyntaxError as erro:
        return {"unidades": [], "custo": 0, "orcamento": ORCAMENTO, "erros": erros_do_programa(erro)}
    erros = erros_do_programa(ErroSemantico(analisador.erros)) if analisador.erros else []
    return {**analisador.resumo(), "erros": erros}


def codigo_do_inimigo(ocupados: Set[str], aleatorio: random.Random) -> str:
    """Monta, em TankScript, uma frota aleatória que gasta o mesmo orçamento do jogador."""
    restante = ORCAMENTO
    frota = []
    while True:
        opcoes = [tipo for tipo in UNIDADES if custo(tipo, 1) <= restante]
        if not opcoes:
            break
        tipo = aleatorio.choice(opcoes)
        frota.append([tipo, 1])
        restante -= custo(tipo, 1)
    for unidade in aleatorio.sample(frota, len(frota)):
        if restante >= CUSTO_DE_ARMA_EXTRA and unidade[1] < MAXIMO_DE_ARMAS:
            unidade[1] += 1
            restante -= CUSTO_DE_ARMA_EXTRA

    linhas = []
    for tipo, quantidade in frota:
        candidatos = [*NOMES_INIMIGOS[tipo], *(f"{nome}{n}" for n in range(2, 99) for nome in NOMES_INIMIGOS[tipo])]
        nome = next(candidato for candidato in candidatos if candidato not in ocupados)
        ocupados.add(nome)
        arma = UNIDADES[tipo]["armas"][0]
        armas = " ".join(f"{arma} {NOMES_DE_ARMAS[arma]}{indice + 1 if indice else ''}" for indice in range(quantidade))
        linhas.append(f"{tipo} {nome} {{ {armas} }}")
    return "\n".join(linhas)


def _posicionar(partida: Partida, nomes: List[str], x: int) -> None:
    for indice, nome in enumerate(nomes):
        unidade = partida.interpretador.units[nome]
        unidade.x = x
        unidade.y = round((indice + 1) * partida.renderer.height * 10 / (len(nomes) + 1) / 10) * 10


def criar_arena(codigo: str, semente: Optional[int] = None) -> Partida:
    """Modo arena: o jogador declara só o exército; o jogo gera a frota inimiga, as equipes e a batalha."""
    exercito = _verificar(codigo, AnalisadorDoExercito(GridRenderer()))
    jogador = [unidade.IDENTIFIER().getText() for unidade in exercito.declaradas]
    inimigo_codigo = codigo_do_inimigo(set(jogador), random.Random(semente))
    inimigo = [linha.split()[1] for linha in inimigo_codigo.splitlines()]

    partida = Partida("\n".join([
        codigo,
        "",
        inimigo_codigo,
        f"team Jogador {{ {' '.join(jogador)} }}",
        f"team Inimigo {{ {' '.join(inimigo)} }}",
        "battle Arena { Jogador vs Inimigo }",
    ]))
    partida.codigo_do_inimigo = inimigo_codigo
    _posicionar(partida, jogador, COLUNA_DO_JOGADOR)
    _posicionar(partida, inimigo, COLUNA_DO_INIMIGO)
    partida.estado_inicial = partida.estado()
    return partida
