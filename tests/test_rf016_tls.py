"""RF-016: la conexión con la BD va siempre cifrada con TLS.

Las pruebas con BD se saltan si MariaDB no está disponible. La de la CA
falsa usa openssl para crear otra autoridad.

    python -m unittest -v tests.test_rf016_tls
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pymysql

from app import config
from app.model import repositorio

VERSIONES_TLS = {"TLSv1.2", "TLSv1.3"}  # RNF-02: TLS 1.2 o superior

# Error de MariaDB al entrar sin cumplir REQUIRE SSL (acceso denegado)
ERROR_ACCESO = 1045


def _usuarios_bd() -> dict[str, tuple[str, str]]:
    usuarios = {config.DB_USUARIO_LOGIN: repositorio._credenciales_login()}
    usuarios.update({u: (u, c) for u, c in config.USUARIOS_PERFIL.values()})
    return usuarios


def _hay_bd() -> bool:
    try:
        repositorio._conectar(*repositorio._credenciales_login()).close()
        return True
    except pymysql.Error:
        return False


def _conectar_sin_repositorio(usuario: str, contrasena: str, **ssl) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=config.DB_HOST, port=config.DB_PORT, user=usuario, password=contrasena,
        database=config.DB_NAME, connect_timeout=5, **ssl,
    )


class PruebasConfiguracion(unittest.TestCase):
    """No usan BD."""

    def test_conecta_con_tls_y_comprueba_el_certificado(self):
        with mock.patch.object(repositorio.pymysql, "connect") as conectar:
            repositorio._conectar("usuario", "contrasena")
        opciones = conectar.call_args.kwargs
        self.assertEqual(opciones["ssl_ca"], config.DB_SSL_CA)
        self.assertTrue(opciones["ssl_verify_cert"])
        self.assertTrue(opciones["ssl_verify_identity"])

    def test_ruta_de_la_ca_absoluta(self):
        self.assertTrue(Path(config.DB_SSL_CA).is_absolute())

    def test_certificados_fuera_de_git(self):
        gitignore = (config.RAIZ / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("db/certificados/", gitignore.splitlines())


@unittest.skipUnless(_hay_bd(), "MariaDB no disponible o sin TLS configurado")
class PruebasTlsEnBD(unittest.TestCase):

    def test_todas_las_conexiones_van_cifradas(self):
        for usuario, credenciales in _usuarios_bd().items():
            with self.subTest(usuario=usuario):
                with repositorio._conectar(*credenciales) as conexion, \
                        conexion.cursor() as cursor:
                    cursor.execute("SHOW SESSION STATUS LIKE 'Ssl_version'")
                    self.assertIn(cursor.fetchone()["Value"], VERSIONES_TLS)
                    cursor.execute("SHOW SESSION STATUS LIKE 'Ssl_cipher'")
                    self.assertNotEqual(cursor.fetchone()["Value"], "")

    def test_sin_tls_no_deja_entrar(self):
        for usuario, (nombre, contrasena) in _usuarios_bd().items():
            with self.subTest(usuario=usuario):
                with self.assertRaises(pymysql.Error) as error:
                    # PyMySQL cifra por defecto si puede: aquí se desactiva a propósito
                    _conectar_sin_repositorio(nombre, contrasena, ssl_disabled=True).close()
                self.assertEqual(error.exception.args[0], ERROR_ACCESO)

    @unittest.skipUnless(shutil.which("openssl"), "Falta openssl")
    def test_rechaza_un_servidor_firmado_por_otra_ca(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ca_falsa = Path(carpeta) / "ca.pem"
            subprocess.run(
                ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                 "-subj", "/CN=CA falsa", "-days", "1",
                 "-keyout", str(Path(carpeta) / "ca-key.pem"), "-out", str(ca_falsa)],
                check=True, capture_output=True,
            )
            usuario, contrasena = repositorio._credenciales_login()
            with self.assertRaises(pymysql.Error):
                _conectar_sin_repositorio(
                    usuario, contrasena, ssl_ca=str(ca_falsa), ssl_verify_cert=True
                ).close()


if __name__ == "__main__":
    unittest.main()
