"""RF-006: aviso a los jefes cuando se bloquea una cuenta.

Usan la BD de prueba (./db/reset_db.sh) y se saltan si MariaDB no está
disponible. Van en una transacción que se deshace al acabar.

    python -m unittest -v tests.test_rf006_notificacion
"""

import unittest
from unittest import mock

from app import config
from app.model import repositorio
from app.model.repositorio import ErrorBaseDatos
from tests.bd import LOGINS_PRUEBA, PruebaConTransaccion, hay_bd

# Quién se entera si se bloquea una cuenta de Tech: jefe y subjefe de Seguridad y de Tech
AVISADOS_TECH = {"jefe_seg", "subjefe_seg", "jefe_tech", "subjefe_tech"}


@unittest.skipUnless(hay_bd(), "MariaDB no disponible")
class PruebasNotificacion(PruebaConTransaccion):

    def setUp(self):
        super().setUp()
        self.cuentas = {login: repositorio.buscar_por_login(login)
                        for login in LOGINS_PRUEBA + ("tech_bloqueado",)}

    def _avisos(self, login: str) -> list[dict]:
        """Avisos sin leer de login, pedidos con el usuario de BD de su perfil."""
        cuenta = self.cuentas[login]
        with mock.patch.object(repositorio, "_perfil_conectado", cuenta["perfil"]):
            return repositorio.mis_notificaciones(cuenta["id_usuario"])

    def _avisos_de(self, login: str, afectado: str) -> list[dict]:
        return [a for a in self._avisos(login) if a["login_afectado"] == afectado]

    def _marcar(self, login: str, id_notificacion: int) -> None:
        cuenta = self.cuentas[login]
        with mock.patch.object(repositorio, "_perfil_conectado", cuenta["perfil"]):
            repositorio.marcar_notificacion_leida(cuenta["id_usuario"], id_notificacion)

    def _bloquear(self, login: str) -> None:
        for _ in range(config.MAX_INTENTOS_FALLIDOS):
            repositorio.registrar_fallo(login, config.MAX_INTENTOS_FALLIDOS)
        self.assertEqual(repositorio.buscar_por_login(login)["estado"], "bloqueado")

    def test_cuenta_ya_bloqueada_avisa(self):
        # tech_bloqueado empieza bloqueada en el 003, antes de que exista la tabla
        avisos = self._avisos_de("jefe_seg", "tech_bloqueado")
        self.assertEqual(len(avisos), 1)
        self.assertEqual(set(avisos[0]), {"id_notificacion", "tipo", "fecha",
                                          "nombre_afectado", "login_afectado"})
        self.assertEqual(avisos[0]["tipo"], "bloqueo_cuenta")
        self.assertEqual(avisos[0]["nombre_afectado"], "Tomás Gil")

    def test_destinatarios_del_bloqueo(self):
        self._bloquear("tech1")
        for login in LOGINS_PRUEBA:
            if login == "tech1":
                continue
            with self.subTest(login=login):
                esperado = 1 if login in AVISADOS_TECH else 0
                self.assertEqual(len(self._avisos_de(login, "tech1")), esperado)

    def test_bloqueo_de_un_jefe(self):
        # Se enteran Seguridad y el subjefe de su perfil; él no se avisa a sí mismo
        self._bloquear("jefe_cien")
        for login in ("jefe_seg", "subjefe_seg", "subjefe_cien"):
            with self.subTest(login=login):
                self.assertEqual(len(self._avisos_de(login, "jefe_cien")), 1)
        for login in ("jefe_tech", "subjefe_tech", "jefesector_cien", "cientifico1"):
            with self.subTest(login=login):
                self.assertEqual(self._avisos_de(login, "jefe_cien"), [])

    def test_solo_avisa_al_pasar_a_bloqueado(self):
        self._bloquear("tech1")
        # Más fallos o cambiar los intentos de una cuenta ya bloqueada no avisan otra vez
        repositorio.registrar_fallo("tech1", config.MAX_INTENTOS_FALLIDOS)
        repositorio.actualizar_intentos(self.cuentas["tech1"]["id_usuario"], 7)
        self.assertEqual(len(self._avisos_de("jefe_seg", "tech1")), 1)

    def test_un_fallo_sin_bloquear_no_avisa(self):
        repositorio.registrar_fallo("tech1", config.MAX_INTENTOS_FALLIDOS)
        self.assertEqual(self._avisos_de("jefe_seg", "tech1"), [])

    def test_marcar_como_leida(self):
        aviso = self._avisos_de("jefe_seg", "tech_bloqueado")[0]
        self._marcar("jefe_seg", aviso["id_notificacion"])
        self.assertEqual(self._avisos_de("jefe_seg", "tech_bloqueado"), [])
        # Cada destinatario tiene la suya: a los demás les sigue saliendo
        self.assertEqual(len(self._avisos_de("subjefe_seg", "tech_bloqueado")), 1)

    # Una prueba por perfil: en la misma transacción, dos conexiones que tocan
    # la misma fila se esperarían la una a la otra
    def test_no_marca_la_de_otro(self):
        aviso = self._avisos_de("jefe_seg", "tech_bloqueado")[0]
        self._marcar("subjefe_seg", aviso["id_notificacion"])
        self.assertEqual(len(self._avisos_de("jefe_seg", "tech_bloqueado")), 1)

    def test_no_marca_la_de_otro_perfil(self):
        aviso = self._avisos_de("jefe_seg", "tech_bloqueado")[0]
        self._marcar("jefe_tech", aviso["id_notificacion"])
        self.assertEqual(len(self._avisos_de("jefe_seg", "tech_bloqueado")), 1)

    def test_con_el_usuario_de_bd_de_otro_perfil(self):
        filas = repositorio._consultar_todos(
            "CALL mis_notificaciones(%s)", (self.cuentas["jefe_seg"]["id_usuario"],),
            config.USUARIOS_PERFIL["tech"],
        )
        self.assertEqual(filas, [])

    def test_sin_sesion(self):
        with mock.patch.object(repositorio, "_perfil_conectado", None), \
                self.assertRaises(ErrorBaseDatos):
            repositorio.mis_notificaciones(self.cuentas["jefe_seg"]["id_usuario"])


@unittest.skipUnless(hay_bd(), "MariaDB no disponible")
class PruebasPermisosNotificacion(PruebaConTransaccion):
    """Nadie lee ni crea avisos fuera de los procedimientos."""

    def test_login_no_puede_leer_avisos(self):
        with self.assertRaises(ErrorBaseDatos):
            repositorio._consultar_todos("CALL mis_notificaciones(%s)", (1,),
                                         repositorio._credenciales_login())

    def test_nadie_toca_la_tabla(self):
        usuarios = [repositorio._credenciales_login(), *config.USUARIOS_PERFIL.values()]
        for credenciales in usuarios:
            with self.subTest(usuario=credenciales[0]):
                with self.assertRaises(ErrorBaseDatos):
                    repositorio._consultar_todos("SELECT * FROM notificacion", (), credenciales)
                with self.assertRaises(ErrorBaseDatos):
                    repositorio._ejecutar(
                        "INSERT INTO notificacion (id_destinatario, tipo, id_usuario_afectado)"
                        " VALUES (1, 'bloqueo_cuenta', 2)", (), credenciales)


if __name__ == "__main__":
    unittest.main()
