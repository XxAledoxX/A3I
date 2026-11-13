"""RF-010: pruebas del bloqueo de cuenta (RF-006) y de la sesión (RF-009).

Las del bloqueo usan la BD de prueba (./db/reset_db.sh) y se saltan si
MariaDB no está disponible. Al terminar cada prueba se dejan los intentos
y el estado de todas las cuentas como estaban. Las de la sesión no usan BD
y van con Qt sin pantalla (QT_QPA_PLATFORM=offscreen).

    python -m unittest -v tests.test_rf010_bloqueo_sesion
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pymysql
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from app import config
from app.controller import controlador_login
from app.controller.controlador_login import ControladorLogin
from app.model import autenticacion, repositorio
from app.model.usuario import Usuario

# Cuenta que se bloquea en las pruebas y otra para comprobar que no cambia
LOGIN = "tech2"
CONTRASENA = "Tech2.Prueba"
OTRO_LOGIN = "tech1"
OTRA_CONTRASENA = "Tech1.Prueba"

MAXIMO = config.MAX_INTENTOS_FALLIDOS

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


def _poner_cuenta(login: str, intentos: int, estado: str) -> None:
    with repositorio._conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute(
            "UPDATE usuario SET intentos_fallidos = %s, estado = %s WHERE login = %s",
            (intentos, estado, login),
        )


def _fallar(login: str, veces: int) -> None:
    for _ in range(veces):
        autenticacion.autenticar(login, "incorrecta")


@unittest.skipUnless(_hay_bd(), "MariaDB no disponible")
class PruebasBloqueo(unittest.TestCase):

    def setUp(self):
        self.cuentas_antes = _estado_cuentas()
        for login, (intentos, estado) in self.cuentas_antes.items():
            if estado != "activo" or intentos:
                self.skipTest(f"{login} no está como recién creada: ejecuta ./db/reset_db.sh")

    def tearDown(self):
        # Deja las cuentas como estaban aunque la prueba falle
        for login, (intentos, estado) in self.cuentas_antes.items():
            _poner_cuenta(login, intentos, estado)

    def test_por_debajo_del_maximo_no_bloquea(self):
        _fallar(LOGIN, MAXIMO - 1)
        self.assertEqual(_estado_cuentas()[LOGIN], (MAXIMO - 1, "activo"))
        self.assertIsNotNone(autenticacion.autenticar(LOGIN, CONTRASENA))

    def test_al_llegar_al_maximo_bloquea(self):
        _fallar(LOGIN, MAXIMO)
        self.assertEqual(_estado_cuentas()[LOGIN], (MAXIMO, "bloqueado"))

    def test_cuenta_bloqueada_no_entra_con_la_contrasena_correcta(self):
        _fallar(LOGIN, MAXIMO)
        self.assertIsNone(autenticacion.autenticar(LOGIN, CONTRASENA))

    def test_fallos_con_la_cuenta_bloqueada_no_suben_el_contador(self):
        _fallar(LOGIN, MAXIMO + 3)
        self.assertEqual(_estado_cuentas()[LOGIN], (MAXIMO, "bloqueado"))

    def test_login_correcto_pone_el_contador_a_cero(self):
        _fallar(LOGIN, MAXIMO - 1)
        self.assertIsNotNone(autenticacion.autenticar(LOGIN, CONTRASENA))
        self.assertEqual(_estado_cuentas()[LOGIN], (0, "activo"))
        # Vuelven a hacer falta todos los fallos para bloquear
        _fallar(LOGIN, MAXIMO - 1)
        self.assertEqual(_estado_cuentas()[LOGIN], (MAXIMO - 1, "activo"))

    def test_bloquear_una_cuenta_no_cambia_las_demas(self):
        _fallar(LOGIN, MAXIMO)
        esperado = dict(self.cuentas_antes)
        esperado[LOGIN] = (MAXIMO, "bloqueado")
        self.assertEqual(_estado_cuentas(), esperado)
        self.assertIsNotNone(autenticacion.autenticar(OTRO_LOGIN, OTRA_CONTRASENA))

    def test_cuenta_desactivada_no_entra(self):
        _poner_cuenta(LOGIN, 0, "desactivado")
        self.assertIsNone(autenticacion.autenticar(LOGIN, CONTRASENA))
        _fallar(LOGIN, MAXIMO)
        self.assertEqual(_estado_cuentas()[LOGIN], (0, "desactivado"))

    def test_login_inexistente_no_bloquea_nada(self):
        _fallar("noexiste", MAXIMO + 1)
        self.assertEqual(_estado_cuentas(), self.cuentas_antes)

    def test_cuenta_bloqueada_ve_el_mismo_mensaje(self):
        app = QApplication.instance() or QApplication([])
        controlador = ControladorLogin()
        try:
            controlador.iniciar_sesion(LOGIN, "incorrecta")
            mensaje_contrasena = controlador.ventana_login.error.text()
            _fallar(LOGIN, MAXIMO)
            controlador.iniciar_sesion(LOGIN, CONTRASENA)
            self.assertIsNone(controlador.ventana_principal)
            self.assertEqual(controlador.ventana_login.error.text(), mensaje_contrasena)
        finally:
            controlador.ventana_login.close()
            controlador.ventana_login.deleteLater()
            app.processEvents()


class PruebasSesion(unittest.TestCase):
    """Cierre de sesión y cierre por inactividad. autenticar se simula."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.controlador = ControladorLogin()
        with mock.patch.object(
            controlador_login.autenticacion, "autenticar", return_value=USUARIO_EJEMPLO
        ):
            self.controlador.iniciar_sesion("tech1", "Tech1.Prueba")
        self.ventana_principal = self.controlador.ventana_principal

    def tearDown(self):
        if self.controlador.ventana_principal is not None:
            self.controlador.cerrar_sesion()
        self.controlador.ventana_login.close()
        self.controlador.ventana_login.deleteLater()
        self.app.processEvents()

    def _pulsar_tecla(self, widget) -> None:
        evento = QKeyEvent(QEvent.KeyPress, Qt.Key_A, Qt.NoModifier, "a")
        QApplication.sendEvent(widget, evento)

    def test_al_entrar_arranca_el_temporizador(self):
        temporizador = self.controlador.temporizador
        self.assertTrue(temporizador.isActive())
        self.assertEqual(temporizador.interval(), config.MINUTOS_INACTIVIDAD * 60 * 1000)

    def test_cerrar_sesion_vuelve_al_login(self):
        self.ventana_principal.boton_cerrar.click()
        self.assertIsNone(self.controlador.ventana_principal)
        self.assertFalse(self.ventana_principal.isVisible())
        self.assertTrue(self.controlador.ventana_login.isVisible())
        self.assertFalse(self.controlador.temporizador.isActive())

    def test_cerrar_sesion_no_muestra_error(self):
        self.ventana_principal.boton_cerrar.click()
        self.assertTrue(self.controlador.ventana_login.error.isHidden())

    def test_inactividad_cierra_la_sesion_y_avisa(self):
        # Lo mismo que pasa cuando vence el temporizador
        self.controlador.temporizador.timeout.emit()
        self.assertIsNone(self.controlador.ventana_principal)
        self.assertTrue(self.controlador.ventana_login.isVisible())
        self.assertEqual(
            self.controlador.ventana_login.error.text(),
            controlador_login.MENSAJE_INACTIVIDAD,
        )

    def test_actividad_reinicia_el_temporizador(self):
        for tipo in controlador_login.EVENTOS_ACTIVIDAD:
            with self.subTest(evento=tipo):
                self.controlador.temporizador.stop()
                self.controlador.detector.eventFilter(self.ventana_principal, QEvent(tipo))
                self.assertTrue(self.controlador.temporizador.isActive())

    def test_mover_el_raton_no_cuenta_como_actividad(self):
        self.controlador.temporizador.stop()
        self.controlador.detector.eventFilter(
            self.ventana_principal, QEvent(QEvent.MouseMove)
        )
        self.assertFalse(self.controlador.temporizador.isActive())

    def test_pulsar_una_tecla_en_la_ventana_reinicia_el_temporizador(self):
        self.controlador.temporizador.stop()
        self._pulsar_tecla(self.ventana_principal)
        self.assertTrue(self.controlador.temporizador.isActive())

    def test_tras_cerrar_sesion_no_se_vigila_la_actividad(self):
        self.controlador.cerrar_sesion()
        self._pulsar_tecla(self.controlador.ventana_login)
        self.assertFalse(self.controlador.temporizador.isActive())


if __name__ == "__main__":
    unittest.main()
