"""Validación de las entradas del usuario (RF-015)."""

import re

from app import config

_PATRON_LOGIN = re.compile(config.PATRON_LOGIN)


def login_valido(login: str) -> bool:
    """True si el login tiene el formato permitido (ver config.PATRON_LOGIN)."""
    # fullmatch y no match con $: "$" también acepta un salto de línea al final
    return isinstance(login, str) and _PATRON_LOGIN.fullmatch(login) is not None
