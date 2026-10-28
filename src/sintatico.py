import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tankscript.arvore import arvore_como_texto


def main(argv=None):
    argument_parser = argparse.ArgumentParser(
        description="Mostra a árvore sintática de um arquivo TankScript."
    )
    argument_parser.add_argument("programa", type=Path, help="caminho para o arquivo .tank")
    arguments = argument_parser.parse_args(argv)

    try:
        source = arguments.programa.read_text(encoding="utf-8")
        print(arvore_como_texto(source))
    except (OSError, SyntaxError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
