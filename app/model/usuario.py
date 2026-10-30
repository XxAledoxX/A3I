from dataclasses import dataclass


@dataclass(frozen=True)
class Usuario:
    """Usuario que ha iniciado sesión (sin el hash)."""

    id_usuario: int
    nombre: str
    login: str
    perfil: str
    nivel: int
    rango: str
