"""RF-013: el login va con a3i_login y luego se usa el usuario de BD del perfil.

Lo que puede y no puede hacer cada usuario de BD está en
test_rf020_permisos.py. Las pruebas con BD se saltan si MariaDB no está
disponible.

    python -m unittest -v tests.test_rf013_control_acceso
"""

import unittest
from unittest import mock

import pymysql

from app import config
from app.model import autenticacion, repositorio

LOGIN = "tech1"
CONTRASENA = "Tech1.Prueba"


def _hay_bd() -> bool:
    try:
        repositorio._conectar(*repositorio._credenciales_login()).close()
        return True
    except pymysql.Error:
        return False


class PruebasReconexion(unittest.TestCase):
    """No usan BD: se simula la conexión."""

    def setUp(self):
        repositorio.desconectar_perfil()
        self.addCleanup(repositorio.desconectar_perfil)

    def test_sin_sesion_no_hay_usuario_de_perfil(self):
        with self.assertRaises(repositorio.ErrorBaseDatos):
            repositorio._credenciales_perfil()

    def test_conectar_perfil_usa_su_usuario(self):
        for perfil, (usuario, contrasena) in config.USUARIOS_PERFIL.items():
            with self.subTest(perfil=perfil), \
                    mock.patch.object(repositorio, "_conectar") as conectar:
                repositorio.conectar_perfil(perfil)
                conectar.assert_called_once_with(usuario, contrasena)
                self.assertEqual(repositorio._credenciales_perfil(), (usuario, contrasena))

    def test_si_falla_la_conexion_no_queda_sesion(self):
        error = pymysql.err.OperationalError(1045, "Access denied")
        with mock.patch.object(repositorio, "_conectar", side_effect=error):
            with self.assertRaises(repositorio.ErrorBaseDatos):
                repositorio.conectar_perfil("tech")
        with self.assertRaises(repositorio.ErrorBaseDatos):
            repositorio._credenciales_perfil()

    def test_desconectar(self):
        with mock.patch.object(repositorio, "_conectar"):
            repositorio.conectar_perfil("tech")
        autenticacion.cerrar_sesion()
        with self.assertRaises(repositorio.ErrorBaseDatos):
            repositorio._credenciales_perfil()

    def test_perfil_desconocido(self):
        with self.assertRaises(KeyError):
            repositorio.conectar_perfil("admin")


@unittest.skipUnless(_hay_bd(), "MariaDB no disponible")
class PruebasLoginConUsuariosDeBD(unittest.TestCase):

    def setUp(self):
        repositorio.desconectar_perfil()
        self.addCleanup(repositorio.desconectar_perfil)
        # Apunta con qué usuario de BD se abre cada conexión
        self.usuarios = []
        conectar = repositorio._conectar

        def apuntar(usuario=None, contrasena=None):
            self.usuarios.append(usuario)
            return conectar(usuario, contrasena)

        parche = mock.patch.object(repositorio, "_conectar", side_effect=apuntar)
        parche.start()
        self.addCleanup(parche.stop)

    def test_login_correcto_usa_a3i_login_y_luego_el_perfil(self):
        self.assertIsNotNone(autenticacion.autenticar(LOGIN, CONTRASENA))
        self.assertEqual(self.usuarios[-1], "a3i_tech")
        self.assertEqual(set(self.usuarios[:-1]), {config.DB_USUARIO_LOGIN})
        self.assertEqual(repositorio._credenciales_perfil(), config.USUARIOS_PERFIL["tech"])

    def test_login_fallido_solo_usa_a3i_login(self):
        self.assertIsNone(autenticacion.autenticar(LOGIN, "incorrecta"))
        self.assertEqual(set(self.usuarios), {config.DB_USUARIO_LOGIN})
        with self.assertRaises(repositorio.ErrorBaseDatos):
            repositorio._credenciales_perfil()
        # Deja el contador como estaba
        fila = repositorio.buscar_por_login(LOGIN)
        repositorio.actualizar_intentos(fila["id_usuario"], 0)

    def test_cada_perfil_conecta_con_el_suyo(self):
        for login, contrasena, perfil in (
            ("cientifico1", "Cientifico1.Prueba", "cientificos"),
            ("seguridad1", "Seguridad1.Prueba", "seguridad"),
            ("tech1", "Tech1.Prueba", "tech"),
        ):
            with self.subTest(login=login):
                self.usuarios.clear()
                autenticacion.autenticar(login, contrasena)
                self.assertEqual(self.usuarios[-1], config.USUARIOS_PERFIL[perfil][0])


if __name__ == "__main__":
    unittest.main()
