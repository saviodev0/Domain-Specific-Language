import argparse
import json
import sys
import threading
import uuid
from collections import OrderedDict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tankscript import catalogo
from tankscript.partida import ErroDaPartida, Partida, criar_arena, descrever_mapa, erros_do_programa, verificar_exercito
from tankscript.renderer import GridRenderer
from tankscript.semantico import ErroSemantico

PASTA_WEB = PROJECT_ROOT / "web"
MAXIMO_DE_PARTIDAS = 50
TAMANHO_MAXIMO = 64 * 1024

_partidas: "OrderedDict[str, Partida]" = OrderedDict()
_trava = threading.Lock()


def criar_partida(codigo: str):
    partida = criar_arena(codigo)
    identificador = uuid.uuid4().hex
    _partidas[identificador] = partida
    while len(_partidas) > MAXIMO_DE_PARTIDAS:
        _partidas.popitem(last=False)
    return {
        "id": identificador,
        "mapa": partida.mapa(),
        "estado_inicial": partida.estado_inicial,
        "eventos": partida.eventos_do_cenario,
        "codigo_do_inimigo": partida.codigo_do_inimigo,
        **partida.resumo(),
    }


def jogar_turno(identificador: str, codigo: str):
    partida = _partidas.get(identificador)
    if partida is None:
        raise ErroDaPartida("Partida não encontrada; inicie a batalha de novo")
    eventos = partida.jogar_turno(codigo)
    return {"eventos": eventos, **partida.resumo()}


class Manipulador(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PASTA_WEB), **kwargs)

    def do_GET(self):
        if self.path == "/api/catalogo":
            return self._responder(200, catalogo.descrever())
        if self.path == "/api/mapa":
            return self._responder(200, descrever_mapa(GridRenderer()))
        return super().do_GET()

    def do_POST(self):
        partes = self.path.strip("/").split("/")
        try:
            codigo = self._ler_codigo()
            with _trava:
                if partes == ["api", "exercito"]:
                    return self._responder(200, verificar_exercito(codigo))
                if partes == ["api", "partidas"]:
                    return self._responder(201, criar_partida(codigo))
                if len(partes) == 4 and partes[:2] == ["api", "partidas"] and partes[3] == "turnos":
                    return self._responder(200, jogar_turno(partes[2], codigo))
            return self._responder(404, {"erros": [{"mensagem": "Rota não encontrada"}]})
        except (SyntaxError, ErroSemantico) as erro:
            return self._responder(422, {"erros": erros_do_programa(erro)})
        except (ErroDaPartida, ValueError) as erro:
            return self._responder(400, {"erros": [{"mensagem": str(erro)}]})
        except Exception as erro:
            self.log_error("Erro interno: %r", erro)
            return self._responder(500, {"erros": [{"mensagem": f"Erro interno do servidor: {erro}"}]})

    def _ler_codigo(self) -> str:
        tamanho = int(self.headers.get("Content-Length", 0))
        if tamanho > TAMANHO_MAXIMO:
            raise ValueError("Programa grande demais")
        corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        codigo = corpo.get("codigo") if isinstance(corpo, dict) else None
        if not isinstance(codigo, str):
            raise ValueError("Envie o programa no campo 'codigo'")
        return codigo

    def _responder(self, status: int, dados) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


def main(argv=None):
    argument_parser = argparse.ArgumentParser(description="Interface web do TankIO.")
    argument_parser.add_argument("--host", default="127.0.0.1", help="endereço (use 0.0.0.0 no Docker)")
    argument_parser.add_argument("--porta", type=int, default=8000)
    arguments = argument_parser.parse_args(argv)

    servidor = ThreadingHTTPServer((arguments.host, arguments.porta), Manipulador)
    print(f"TankIO em http://{'localhost' if arguments.host == '0.0.0.0' else arguments.host}:{arguments.porta}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
