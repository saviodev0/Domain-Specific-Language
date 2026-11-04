"""Atributos fixos de cada tipo de unidade e de arma. Declarar uma unidade só cria uma instância
do tipo: o programa escolhe o nome e as armas, nunca os números."""

# radar e sonar em unidades do mapa: cada célula tem 10, então radar 20 enxerga 2 casas ao redor.
UNIDADES = {
    "tank": {"hp": 120, "armor": 15, "speed": 30, "radar": 20, "sonar": 30, "custo": 4, "armas": ("gun",)},
    "submarine": {"hp": 90, "armor": 10, "speed": 25, "radar": 20, "sonar": 40, "custo": 5, "armas": ("torpedo",)},
    "aircraft": {"hp": 70, "armor": 5, "speed": 60, "radar": 20, "sonar": 40, "custo": 4, "armas": ("missile",)},
}

ARMAS = {
    "gun": {"damage": 40, "range": 60, "ammo": 6, "cooldown": 1},
    "torpedo": {"damage": 70, "range": 80, "ammo": 3, "cooldown": 2},
    "missile": {"damage": 55, "range": 100, "ammo": 2, "cooldown": 2},
}

ATRIBUTOS = ("hp", "armor", "speed", "radar")
MAXIMO_DE_ARMAS = 2
CUSTO_DE_ARMA_EXTRA = 1
ORCAMENTO = 20
RECARGA_DO_SONAR = 2


def custo(tipo: str, quantidade_de_armas: int) -> int:
    return UNIDADES[tipo]["custo"] + CUSTO_DE_ARMA_EXTRA * max(0, quantidade_de_armas - 1)


def descrever() -> dict:
    return {
        "unidades": {tipo: {**dados, "armas": list(dados["armas"])} for tipo, dados in UNIDADES.items()},
        "armas": ARMAS,
        "maximo_de_armas": MAXIMO_DE_ARMAS,
        "custo_de_arma_extra": CUSTO_DE_ARMA_EXTRA,
        "orcamento": ORCAMENTO,
        "recarga_do_sonar": RECARGA_DO_SONAR,
    }
