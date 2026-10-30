"""RF-015: el campo login solo acepta el formato permitido.

No necesitan BD: un login no válido se rechaza antes de consultarla. Las
pruebas de la ventana usan Qt sin pantalla (QT_QPA_PLATFORM=offscreen).

    python -m unittest -v tests.test_rf015_validacion
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QApplication

from app import config
from app.model import autenticacion
from app.model.validacion import login_valido
from app.view.ventana_login import VentanaLogin

VALIDOS = (
    "cientifico1",
    "seguridad1",
    "tech1",
    "Tech1",
    "abc",
    "a" * config.LONGITUD_MAXIMA_LOGIN,
    "nombre.apellido",
    "nombre_apellido-2",
)

NO_VALIDOS = (
    "",
    "ab",
    "a" * (config.LONGITUD_MAXIMA_LOGIN + 1),
    " tech1",
    "tech1 ",
    "tech 1",
    "tech1\n",
    "tech1\t",
    "tech1\x00",
    "técnico",
    "ñandú",
    "tech١",  # dígito árabe: \d lo aceptaría
    "tech1@a3i",
    "' OR '1'='1",
    "' OR 1=1 -- ",
    "cientifico1' -- ",
    "x'; UPDATE usuario SET estado = 'bloqueado'; -- ",
    "<script>",
    "tech1%",
)


class PruebasLoginValido(unittest.TestCase):

    def test_logins_validos(self):
        for login in VALIDOS:
            with self.subTest(login=login):
                self.assertTrue(login_valido(login))

    def test_logins_no_validos(self):
        for login in NO_VALIDOS:
            with self.subTest(login=login):
                self.assertFalse(login_valido(login))

    def test_tipo_no_texto(self):
        for login in (None, 123, b"tech1", ["tech1"]):
            with self.subTest(login=login):
                self.assertFalse(login_valido(login))


class PruebasAutenticar(unittest.TestCase):

    def test_login_no_valido_no_consulta_la_bd(self):
        with mock.patch.object(autenticacion, "repositorio") as repositorio:
            for login in NO_VALIDOS:
                with self.subTest(login=login):
                    self.assertIsNone(autenticacion.autenticar(login, "x"))
            repositorio.buscar_por_login.assert_not_called()
            repositorio.registrar_fallo.assert_not_called()

    def test_login_valido_si_consulta_la_bd(self):
        # Control: si esto falla, la prueba anterior no demuestra nada
        with mock.patch.object(autenticacion, "repositorio") as repositorio:
            repositorio.buscar_por_login.return_value = None
            self.assertIsNone(autenticacion.autenticar("tech1", "x"))
            repositorio.buscar_por_login.assert_called_once_with("tech1")


class PruebasVentana(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.ventana = VentanaLogin()
        self.campo = self.ventana.usuario

    def tearDown(self):
        self.ventana.deleteLater()

    def test_longitud_maxima(self):
        self.assertEqual(self.campo.maxLength(), config.LONGITUD_MAXIMA_LOGIN)

    def test_no_deja_escribir_caracteres_no_validos(self):
        validador = self.campo.validator()
        for texto in ("tech 1", "técnico", "' OR 1=1", "tech1@"):
            with self.subTest(texto=texto):
                estado, _, _ = validador.validate(texto, len(texto))
                self.assertEqual(estado, QValidator.State.Invalid)

    def test_login_corto_es_intermedio(self):
        # Mientras se escribe sí se deja, aunque aún no sea válido
        estado, _, _ = self.campo.validator().validate("ab", 2)
        self.assertEqual(estado, QValidator.State.Intermediate)

    def test_login_valido_es_aceptable(self):
        estado, _, _ = self.campo.validator().validate("tech1", 5)
        self.assertEqual(estado, QValidator.State.Acceptable)


if __name__ == "__main__":
    unittest.main()
