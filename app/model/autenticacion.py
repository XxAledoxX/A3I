"""Login de usuarios."""

from app import config
from app.model import repositorio
from app.model.usuario import Usuario

# Hash de prueba para cuando el usuario no existe (así tarda lo mismo)
HASH_FICTICIO: str = ""


def autenticar(login: str, contrasena: str) -> Usuario | None:
    """Devuelve el Usuario si el login es correcto, si no None."""
    fila = repositorio.buscar_por_login(login)
    if fila is None:
        _verificar_contrasena(HASH_FICTICIO, contrasena)
        _registrar_fallo(login)
        return None

    # Se comprueba la contraseña antes que el estado para que tarde lo mismo
    correcta = _verificar_contrasena(fila["hash_contrasena"], contrasena)
    if fila["estado"] != "activo" or not correcta:
        _registrar_fallo(login)
        return None

    if fila["intentos_fallidos"]:
        repositorio.actualizar_intentos(fila["id_usuario"], 0)
    if _necesita_rehash(fila["hash_contrasena"]):
        repositorio.actualizar_hash(fila["id_usuario"], _generar_hash(contrasena))

    return Usuario(
        id_usuario=fila["id_usuario"],
        nombre=fila["nombre"],
        login=fila["login"],
        perfil=fila["perfil"],
        nivel=fila["nivel"],
        rango=fila["rango"],
    )


def _verificar_contrasena(hash_guardado: str, contrasena: str) -> bool:
    raise NotImplementedError("RF-005")


def _necesita_rehash(hash_guardado: str) -> bool:
    raise NotImplementedError("RF-005")


def _generar_hash(contrasena: str) -> str:
    raise NotImplementedError("RF-005")


def _registrar_fallo(login: str) -> None:
    # Se llama en todos los fallos para que tarden lo mismo.
    # Si el usuario no existe o no está activo, no cambia nada
    repositorio.registrar_fallo(login, config.MAX_INTENTOS_FALLIDOS)
