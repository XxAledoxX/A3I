"""Login de usuarios."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app import config
from app.model import repositorio, validacion
from app.model.usuario import Usuario

# Argon2id con los parámetros por defecto (m=64 MiB, t=3, p=4).
# Cada hash lleva su propia sal aleatoria y los parámetros dentro
_hasher = PasswordHasher()

# Hash de prueba para cuando el usuario no existe (así tarda lo mismo)
HASH_FICTICIO: str = _hasher.hash("contrasena-ficticia")


def autenticar(login: str, contrasena: str) -> Usuario | None:
    """Devuelve el Usuario si el login es correcto, si no None."""
    # Un login con formato no válido no puede existir: no se consulta la BD.
    # Que tarde menos no da pistas, el formato es público
    if not validacion.login_valido(login):
        return None

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
    try:
        return _hasher.verify(hash_guardado, contrasena)
    except (VerificationError, InvalidHashError):
        return False


def _necesita_rehash(hash_guardado: str) -> bool:
    # True si el hash se hizo con otros parámetros que los actuales
    return _hasher.check_needs_rehash(hash_guardado)


def _generar_hash(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def _registrar_fallo(login: str) -> None:
    # Se llama en todos los fallos para que tarden lo mismo.
    # Si el usuario no existe o no está activo, no cambia nada
    repositorio.registrar_fallo(login, config.MAX_INTENTOS_FALLIDOS)
