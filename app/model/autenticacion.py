"""Login de usuarios."""

from app.model.usuario import Usuario

# Hash de prueba para cuando el usuario no existe (así tarda lo mismo)
HASH_FICTICIO: str = ""


def autenticar(login: str, contrasena: str) -> Usuario | None:
    """Devuelve el Usuario si el login es correcto, si no None."""
    raise NotImplementedError("RF-004")


def _verificar_contrasena(hash_guardado: str, contrasena: str) -> bool:
    raise NotImplementedError("RF-005")


def _necesita_rehash(hash_guardado: str) -> bool:
    raise NotImplementedError("RF-005")


def _generar_hash(contrasena: str) -> str:
    raise NotImplementedError("RF-005")


def _registrar_fallo(fila: dict) -> None:
    raise NotImplementedError("RF-006")
