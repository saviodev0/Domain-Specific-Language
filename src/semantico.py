import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tankscript.semantico import ErroSemantico, analisar


def main(argv=None):
    argument_parser = argparse.ArgumentParser(
        description="Verifica nomes e tipos de um arquivo TankScript."
    )
    argument_parser.add_argument("programa", type=Path, help="caminho para o arquivo .tank")
    arguments = argument_parser.parse_args(argv)

    try:
        source = arguments.programa.read_text(encoding="utf-8")
        resultado = analisar(source)
    except (OSError, SyntaxError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    except ErroSemantico as error:
        for mensagem in error.erros:
            print(f"Erro semântico: {mensagem}", file=sys.stderr)
        print(f"{len(error.erros)} erro(s) semântico(s)", file=sys.stderr)
        return 1

    print(
        f"Sem erros semânticos: {len(resultado.unidades)} unidade(s), "
        f"{len(resultado.equipes)} equipe(s), {len(resultado.batalhas)} batalha(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
