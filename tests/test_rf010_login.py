"""RF-010: pruebas de inicio de sesión (Sprint 1).

Solo credenciales válidas, contraseña errónea y usuario inexistente. El
bloqueo de cuenta y las sesiones quedan para otro sprint.

Las pruebas con BD usan la de prueba (./db/reset_db.sh) y se saltan si
MariaDB no está disponible. Un fallo suma un intento a la cuenta, así que
se dejan los intentos como estaban. Las del controlador no usan BD y van
con Qt sin pantalla (QT_QPA_PLATFORM=offscreen).

    python -m unittest -v tests.test_rf010_login
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pymysql
from PySide6.QtWidgets import QApplication

from app.controller import controlador_login
from app.controller.controlador_login import ControladorLogin
from app.model import autenticacion, repositorio
from app.model.usuario import Usuario

# Usuarios de prueba de db/003_datos_prueba.sql (ver db/README.md)
USUARIOS_PRUEBA = {
    "cientifico1": "Cientifico1.Prueba",
    "seguridad1": "Seguridad1.Prueba",
    "tech1": "Tech1.Prueba",
}

DATOS_ESPERADOS = {
    "cientifico1": ("Lucía Herrera", "cientificos", 2, "empleado"),
    "seguridad1": ("Marcos Ibáñez", "seguridad", 1, "empleado"),
    "tech1": ("Daniel Ortega", "tech", 1, "empleado"),
}

# Logins con formato válido que no están en la BD
INEXISTENTES = ("noexiste", "cientifico2", "admin", "root")

USUARIO_EJEMPLO = Usuario(
    id_usuario=3, nombre="Daniel Ortega", login="tech1",
    perfil="tech", nivel=1, rango="empleado",
)


def _hay_bd() -> bool:
    try:
        repositorio._conectar().close()
        return True
    except pymysql.Error:
        return False


def _estado_cuentas() -> dict[str, tuple]:
    """Intentos fallidos y estado de todas las cuentas."""
    with repositorio._conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute("SELECT login, intentos_fallidos, estado FROM usuario")
        return {
            fila["login"]: (fila["intentos_fallidos"], fila["estado"])
            for fila in cursor.fetchall()
        }


def _contrasenas_erroneas(contrasena: str) -> tuple[str, ...]:
    return (
        "",
        "incorrecta",
        contrasena.lower(),
        contrasena.upper(),
        contrasena + " ",
        " " + contrasena,
        contrasena[:-1],
    )


@unittest.skipUnless(_hay_bd(), "MariaDB no disponible")
class PruebasLoginEnBD(unittest.TestCase):

    def setUp(self):
        self.cuentas_antes = _estado_cuentas()
        for login, (intentos, estado) in self.cuentas_antes.items():
            if estado != "activo":
                self.skipTest(f"{login} está {estado}: ejecuta ./db/reset_db.sh")

    def tearDown(self):
        # Deja los intentos como estaban aunque la prueba falle
        self._restaurar_intentos()

    def _restaurar_intentos(self):
        for login, (intentos, _) in self.cuentas_antes.items():
            fila = repositorio.buscar_por_login(login)
            if fila["intentos_fallidos"] != intentos:
                repositorio.actualizar_intentos(fila["id_usuario"], intentos)

    # Credenciales válidas

    def test_credenciales_validas(self):
        for login, contrasena in USUARIOS_PRUEBA.items():
            with self.subTest(login=login):
                usuario = autenticacion.autenticar(login, contrasena)
                self.assertIsInstance(usuario, Usuario)
                self.assertEqual(usuario.login, login)

    def test_credenciales_validas_devuelven_sus_datos(self):
        for login, (nombre, perfil, nivel, rango) in DATOS_ESPERADOS.items():
            with self.subTest(login=login):
                usuario = autenticacion.autenticar(login, USUARIOS_PRUEBA[login])
                self.assertEqual(usuario.nombre, nombre)
                self.assertEqual(usuario.perfil, perfil)
                self.assertEqual(usuario.nivel, nivel)
                self.assertEqual(usuario.rango, rango)

    def test_credenciales_validas_no_suman_fallos(self):
        for login, contrasena in USUARIOS_PRUEBA.items():
            autenticacion.autenticar(login, contrasena)
        self.assertEqual(_estado_cuentas(), self.cuentas_antes)

    # Contraseña errónea

    def test_contrasena_erronea(self):
        for login, contrasena in USUARIOS_PRUEBA.items():
            for erronea in _contrasenas_erroneas(contrasena):
                with self.subTest(login=login, contrasena=erronea):
                    self.assertIsNone(autenticacion.autenticar(login, erronea))
                # Que no llegue al máximo y bloquee la cuenta
                self._restaurar_intentos()

    def test_contrasena_de_otro_usuario(self):
        self.assertIsNone(
            autenticacion.autenticar("tech1", USUARIOS_PRUEBA["cientifico1"])
        )
        self.assertIsNone(
            autenticacion.autenticar("cientifico1", USUARIOS_PRUEBA["tech1"])
        )

    def test_contrasena_erronea_suma_un_fallo_solo_a_esa_cuenta(self):
        autenticacion.autenticar("tech1", "incorrecta")
        esperado = dict(self.cuentas_antes)
        intentos, estado = esperado["tech1"]
        esperado["tech1"] = (intentos + 1, estado)
        self.assertEqual(_estado_cuentas(), esperado)

    def test_login_correcto_despues_de_un_fallo(self):
        self.assertIsNone(autenticacion.autenticar("tech1", "incorrecta"))
        self.assertIsNotNone(
            autenticacion.autenticar("tech1", USUARIOS_PRUEBA["tech1"])
        )

    # Usuario inexistente

    def test_usuario_inexistente(self):
        for login in INEXISTENTES:
            with self.subTest(login=login):
                self.assertIsNone(autenticacion.autenticar(login, "Tech1.Prueba"))

    def test_usuario_inexistente_con_contrasena_de_otro(self):
        # Las contraseñas de prueba no sirven con un login que no existe
        for contrasena in USUARIOS_PRUEBA.values():
            with self.subTest(contrasena=contrasena):
                self.assertIsNone(autenticacion.autenticar("noexiste", contrasena))

    def test_usuario_inexistente_no_cambia_cuentas(self):
        for login in INEXISTENTES:
            autenticacion.autenticar(login, "incorrecta")
        self.assertEqual(_estado_cuentas(), self.cuentas_antes)


class PruebasControlador(unittest.TestCase):
    """Lo que ve el usuario en cada caso. autenticar se simula: no usa BD."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.controlador = ControladorLogin()
        self.ventana_login = self.controlador.ventana_login

    def tearDown(self):
        if self.controlador.ventana_principal is not None:
            self.controlador.cerrar_sesion()
        self.ventana_login.close()
        self.ventana_login.deleteLater()

    def _iniciar_sesion(self, devuelve, login="tech1", contrasena="x"):
        with mock.patch.object(
            controlador_login.autenticacion, "autenticar", return_value=devuelve
        ) as autenticar:
            self.ventana_login.usuario.setText(login)
            self.ventana_login.contrasena.setText(contrasena)
            self.ventana_login.boton.click()
        autenticar.assert_called_once_with(login, contrasena)

    def test_credenciales_validas_abren_la_ventana_principal(self):
        self._iniciar_sesion(USUARIO_EJEMPLO, "tech1", "Tech1.Prueba")
        self.assertIsNotNone(self.controlador.ventana_principal)
        self.assertTrue(self.controlador.ventana_principal.isVisible())
        self.assertFalse(self.ventana_login.isVisible())

    def test_credenciales_validas_limpian_el_formulario(self):
        self._iniciar_sesion(USUARIO_EJEMPLO, "tech1", "Tech1.Prueba")
        self.assertEqual(self.ventana_login.usuario.text(), "")
        self.assertEqual(self.ventana_login.contrasena.text(), "")

    def test_fallo_muestra_mensaje_y_no_abre_nada(self):
        # Contraseña errónea o usuario inexistente: autenticar da None
        self._iniciar_sesion(None, "tech1", "incorrecta")
        self.assertIsNone(self.controlador.ventana_principal)
        self.assertFalse(self.ventana_login.error.isHidden())
        self.assertEqual(
            self.ventana_login.error.text(), controlador_login.MENSAJE_ERROR
        )

    def test_fallo_borra_la_contrasena_y_deja_el_usuario(self):
        self._iniciar_sesion(None, "tech1", "incorrecta")
        self.assertEqual(self.ventana_login.contrasena.text(), "")
        self.assertEqual(self.ventana_login.usuario.text(), "tech1")

    def test_mismo_mensaje_para_contrasena_erronea_e_inexistente(self):
        self._iniciar_sesion(None, "tech1", "incorrecta")
        mensaje_contrasena = self.ventana_login.error.text()
        self._iniciar_sesion(None, "noexiste", "Tech1.Prueba")
        mensaje_inexistente = self.ventana_login.error.text()
        self.assertEqual(mensaje_contrasena, mensaje_inexistente)

    def test_error_de_bd_muestra_otro_mensaje(self):
        with mock.patch.object(
            controlador_login.autenticacion, "autenticar",
            side_effect=repositorio.ErrorBaseDatos,
        ):
            self.ventana_login.usuario.setText("tech1")
            self.ventana_login.contrasena.setText("x")
            self.ventana_login.boton.click()
        self.assertIsNone(self.controlador.ventana_principal)
        self.assertEqual(
            self.ventana_login.error.text(), controlador_login.MENSAJE_SIN_CONEXION
        )


@unittest.skipUnless(_hay_bd(), "MariaDB no disponible")
class PruebasMismoMensajeEnBD(unittest.TestCase):
    """De punta a punta: contraseña errónea e inexistente se ven igual."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.intentos_antes = repositorio.buscar_por_login("tech1")["intentos_fallidos"]
        self.controlador = ControladorLogin()
        self.ventana_login = self.controlador.ventana_login

    def tearDown(self):
        fila = repositorio.buscar_por_login("tech1")
        if fila["intentos_fallidos"] != self.intentos_antes:
            repositorio.actualizar_intentos(fila["id_usuario"], self.intentos_antes)
        self.ventana_login.close()
        self.ventana_login.deleteLater()

    def _mensaje(self, login, contrasena):
        self.controlador.iniciar_sesion(login, contrasena)
        self.assertIsNone(self.controlador.ventana_principal)
        return self.ventana_login.error.text()

    def test_mismo_mensaje(self):
        self.assertEqual(
            self._mensaje("tech1", "incorrecta"),
            self._mensaje("noexiste", "incorrecta"),
        )


if __name__ == "__main__":
    unittest.main()
