"""Simulador de lecturas: mete una lectura de cada variable cada pocos segundos.

    python simulador.py                   # valores normales, hasta Ctrl+C
    python simulador.py --fuera-de-rango  # una variable se sale de su rango
    python simulador.py --fuego           # el detector de llama marca fuego
    python simulador.py --una-vez         # solo una tanda de lecturas
"""

import argparse
import random
import sys
import time
from datetime import datetime

from app import config
from app.model import repositorio
from app.model.repositorio import ErrorBaseDatos


def valor_normal(variable: dict) -> float:
    """Un valor cerca del centro del rango normal."""
    minimo = float(variable["minimo_normal"])
    maximo = float(variable["maximo_normal"])
    centro = (minimo + maximo) / 2
    margen = (maximo - minimo) / 2
    return round(centro + random.uniform(-0.6, 0.6) * margen, 2)


def valor_fuera_de_rango(variable: dict) -> float:
    """Algo por encima del máximo normal, pero físicamente posible (RF-030)."""
    minimo = float(variable["minimo_normal"])
    maximo = float(variable["maximo_normal"])
    return round(maximo + random.uniform(0.1, 0.3) * (maximo - minimo), 2)


def generar_lecturas(variables: list[dict], fuera_de_rango: bool = False,
                     fuego: bool = False) -> list[tuple[str, int, float]]:
    """Devuelve (nombre, id_variable, valor) de cada variable."""
    numericas = [v["nombre"] for v in variables if v["nombre"] != "llama"]
    rara = random.choice(numericas) if fuera_de_rango and numericas else None

    lecturas = []
    for variable in variables:
        if variable["nombre"] == "llama":
            valor = 1 if fuego else 0
        elif variable["nombre"] == rara:
            valor = valor_fuera_de_rango(variable)
        else:
            valor = valor_normal(variable)
        lecturas.append((variable["nombre"], variable["id_variable"], valor))
    return lecturas


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulador de lecturas de A3I")
    parser.add_argument("--fuera-de-rango", action="store_true",
                        help="cada tanda, una variable fuera de su rango normal")
    parser.add_argument("--fuego", action="store_true", help="el detector de llama marca fuego")
    parser.add_argument("--una-vez", action="store_true", help="solo una tanda y termina")
    args = parser.parse_args()

    try:
        variables = repositorio.variables_simulador()
        print(f"Simulador en marcha: {len(variables)} variables cada "
              f"{config.SEGUNDOS_SIMULADOR} s. Ctrl+C para parar.")
        while True:
            lecturas = generar_lecturas(variables, args.fuera_de_rango, args.fuego)
            for _, id_variable, valor in lecturas:
                repositorio.insertar_lectura(id_variable, valor)
            texto = ", ".join(f"{nombre}={valor:g}" for nombre, _, valor in lecturas)
            print(f"{datetime.now():%H:%M:%S} {texto}")
            if args.una_vez:
                return 0
            time.sleep(config.SEGUNDOS_SIMULADOR)
    except ErrorBaseDatos:
        print("No se puede conectar con la BD: revisa el .env (DB_SIMULADOR_PASSWORD "
              "y DB_SSL_CA) y que MariaDB esté en marcha.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nSimulador parado.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
