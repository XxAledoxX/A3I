"""RF-005: las contraseñas se guardan con hash Argon2id y sal.

Las pruebas con BD usan la de prueba (./db/reset_db.sh) y se saltan si
MariaDB no está disponible. Las que cambian un hash lo dejan como estaba.

    python -m unittest -v tests.test_rf005_hash
"""

import unittest

import pymysql
from argon2 import PasswordHasher, extract_parameters

from app.model import autenticacion, repositorio

# Usuarios de prueba de db/003_datos_prueba.sql (ver db/README.md)
USUARIOS_PRUEBA = {
    "cientifico1": "Cientifico1.Prueba",
    "seguridad1": "Seguridad1.Prueba",
    "tech1": "Tech1.Prueba",
}

CONTRASENA = "Contrasena.Prueba1"

# Mínimo recomendado por la RFC 9106: 16 bytes de sal, 22 caracteres en base64
LONGITUD_MINIMA_SAL = 22


def _sal(hash_argon: str) -> str:
    # $argon2id$v=19$m=...,t=...,p=...$<sal>$<hash>
    return hash_argon.split("$")[4]


def _hay_bd() -> bool:
    try:
        repositorio._conectar().close()
        return True
    except pymysql.Error:
        return False


def _hashes_guardados() -> dict[str, str]:
    with repositorio._conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute("SELECT login, hash_contrasena FROM usuario")
        return {fila["login"]: fila["hash_contrasena"] for fila in cursor.fetchall()}


class PruebasHash(unittest.TestCase):
    """No necesitan BD."""

    def test_usa_argon2id(self):
        hash_nuevo = autenticacion._generar_hash(CONTRASENA)
        self.assertTrue(hash_nuevo.startswith("$argon2id$"))

    def test_parametros_minimos(self):
        # RFC 9106, perfil de poca memoria: 64 MiB y 3 pasadas
        parametros = extract_parameters(autenticacion._generar_hash(CONTRASENA))
        self.assertGreaterEqual(parametros.memory_cost, 65536)
        self.assertGreaterEqual(parametros.time_cost, 3)

    def test_no_guarda_la_contrasena(self):
        hash_nuevo = autenticacion._generar_hash(CONTRASENA)
        self.assertNotIn(CONTRASENA, hash_nuevo)

    def test_misma_contrasena_distinta_sal(self):
        hash_1 = autenticacion._generar_hash(CONTRASENA)
        hash_2 = autenticacion._generar_hash(CONTRASENA)
        self.assertNotEqual(hash_1, hash_2)
        self.assertNotEqual(_sal(hash_1), _sal(hash_2))

    def test_longitud_sal(self):
        sal = _sal(autenticacion._generar_hash(CONTRASENA))
        self.assertGreaterEqual(len(sal), LONGITUD_MINIMA_SAL)

    def test_verifica_contrasena_correcta(self):
        hash_nuevo = autenticacion._generar_hash(CONTRASENA)
        self.assertTrue(autenticacion._verificar_contrasena(hash_nuevo, CONTRASENA))

    def test_rechaza_contrasena_incorrecta(self):
        hash_nuevo = autenticacion._generar_hash(CONTRASENA)
        for contrasena in ("", "contrasena.prueba1", CONTRASENA + " ", CONTRASENA[:-1]):
            with self.subTest(contrasena=contrasena):
                self.assertFalse(
                    autenticacion._verificar_contrasena(hash_nuevo, contrasena)
                )

    def test_hash_mal_formado_no_da_error(self):
        # Si la BD tiene un hash roto, el login falla sin lanzar excepción
        for hash_roto in ("", CONTRASENA, "$argon2id$v=19$roto"):
            with self.subTest(hash_roto=hash_roto):
                self.assertFalse(
                    autenticacion._verificar_contrasena(hash_roto, CONTRASENA)
                )

    def test_hash_actual_no_necesita_rehash(self):
        hash_nuevo = autenticacion._generar_hash(CONTRASENA)
        self.assertFalse(autenticacion._necesita_rehash(hash_nuevo))

    def test_hash_con_parametros_antiguos_necesita_rehash(self):
        antiguo = PasswordHasher(time_cost=1, memory_cost=8192).hash(CONTRASENA)
        self.assertTrue(autenticacion._necesita_rehash(antiguo))

    def test_hash_ficticio_con_mismos_parametros(self):
        # Si no, el login de un usuario que no existe tardaría distinto
        self.assertFalse(autenticacion._necesita_rehash(autenticacion.HASH_FICTICIO))

    def test_hash_ficticio_no_acepta_contrasenas_de_prueba(self):
        for contrasena in USUARIOS_PRUEBA.values():
            with self.subTest(contrasena=contrasena):
                self.assertFalse(
                    autenticacion._verificar_contrasena(
                        autenticacion.HASH_FICTICIO, contrasena
                    )
                )


@unittest.skipUnless(_hay_bd(), "MariaDB no disponible")
class PruebasHashEnBD(unittest.TestCase):

    def setUp(self):
        self.hashes_antes = _hashes_guardados()

    def tearDown(self):
        # Deja los hashes como estaban aunque la prueba falle
        for login, hash_antes in self.hashes_antes.items():
            fila = repositorio.buscar_por_login(login)
            if fila["hash_contrasena"] != hash_antes:
                repositorio.actualizar_hash(fila["id_usuario"], hash_antes)

    def test_hashes_guardados_son_argon2id(self):
        for login, hash_guardado in self.hashes_antes.items():
            with self.subTest(login=login):
                self.assertTrue(hash_guardado.startswith("$argon2id$"))
                self.assertFalse(autenticacion._necesita_rehash(hash_guardado))

    def test_ninguna_contrasena_en_claro(self):
        for login, contrasena in USUARIOS_PRUEBA.items():
            with self.subTest(login=login):
                self.assertNotIn(contrasena, self.hashes_antes[login])

    def test_cada_usuario_tiene_su_sal(self):
        sales = [_sal(hash_guardado) for hash_guardado in self.hashes_antes.values()]
        self.assertEqual(len(sales), len(set(sales)))

    def test_login_con_contrasena_correcta(self):
        for login, contrasena in USUARIOS_PRUEBA.items():
            with self.subTest(login=login):
                usuario = autenticacion.autenticar(login, contrasena)
                self.assertIsNotNone(usuario)
                self.assertEqual(usuario.login, login)
                self.assertFalse(hasattr(usuario, "hash_contrasena"))

    def test_login_rehashea_hash_antiguo(self):
        login, contrasena = "tech1", USUARIOS_PRUEBA["tech1"]
        id_usuario = repositorio.buscar_por_login(login)["id_usuario"]
        antiguo = PasswordHasher(time_cost=1, memory_cost=8192).hash(contrasena)
        repositorio.actualizar_hash(id_usuario, antiguo)

        self.assertIsNotNone(autenticacion.autenticar(login, contrasena))

        nuevo = repositorio.buscar_por_login(login)["hash_contrasena"]
        self.assertNotEqual(nuevo, antiguo)
        self.assertFalse(autenticacion._necesita_rehash(nuevo))
        self.assertTrue(autenticacion._verificar_contrasena(nuevo, contrasena))


if __name__ == "__main__":
    unittest.main()
