"""RF-075: crear, ver y cancelar solicitudes.

Usan la BD de prueba (./db/reset_db.sh) y se saltan si MariaDB no está
disponible. Van en una transacción que se deshace al acabar.

    python -m unittest -v tests.test_rf075_solicitudes
"""

import unittest
from unittest import mock

from app.model import repositorio
from app.model.repositorio import ErrorRegla
from tests.bd import CUENTA_BLOQUEADA, PruebaConTransaccion, hay_bd

COLUMNAS = {"id_solicitud", "tipo", "prioridad", "estado", "fase", "sector", "dispositivo",
            "motivo", "duracion_min", "fecha_creacion", "fecha_resolucion",
            "fecha_caducidad", "aprobaciones"}


@unittest.skipUnless(hay_bd(), "MariaDB no disponible")
class PruebasSolicitudes(PruebaConTransaccion):

    def setUp(self):
        super().setUp()
        self.cuentas = {login: repositorio.buscar_por_login(login)
                        for login in ("tech1", "cientifico1", CUENTA_BLOQUEADA[0])}
        with self._como("tech1"):
            self.sectores = {s["nombre"]: s["id_sector"]
                             for s in repositorio.sectores(self.cuentas["tech1"]["id_usuario"])}

    def _como(self, login: str, perfil: str | None = None):
        """Usa el usuario de BD del perfil de login, o el de otro perfil."""
        return mock.patch.object(repositorio, "_perfil_conectado",
                                 perfil or self.cuentas[login]["perfil"])

    def _dispositivo(self, nombre: str, sector: str) -> int:
        with self._como("tech1"):
            filas = repositorio.dispositivos_sector(self.cuentas["tech1"]["id_usuario"],
                                                    self.sectores[sector])
        return next(f["id_dispositivo"] for f in filas if f["nombre"] == nombre)

    def _crear(self, login: str, tipo: str, sector: str, dispositivo: str | None,
               duracion: int = 30, motivo: str = "Prueba", perfil: str | None = None) -> int:
        id_dispositivo = self._dispositivo(dispositivo, sector) if dispositivo else None
        with self._como(login, perfil):
            return repositorio.crear_solicitud(
                self.cuentas[login]["id_usuario"], tipo, "normal", motivo,
                self.sectores[sector], duracion, id_dispositivo)

    def _mias(self, login: str) -> list[dict]:
        with self._como(login):
            return repositorio.mis_solicitudes(self.cuentas[login]["id_usuario"])

    def _cancelar(self, login: str, id_solicitud: int) -> None:
        with self._como(login):
            repositorio.cancelar_solicitud(self.cuentas[login]["id_usuario"], id_solicitud)

    # Bien

    def test_tech_pide_mantenimiento_de_la_barrera(self):
        id_solicitud = self._crear("tech1", "mantenimiento", "general", "barrera")
        fila = next(f for f in self._mias("tech1") if f["id_solicitud"] == id_solicitud)
        self.assertEqual(set(fila), COLUMNAS)
        self.assertEqual((fila["tipo"], fila["estado"], fila["sector"], fila["dispositivo"]),
                         ("mantenimiento", "pendiente", "general", "barrera"))
        self.assertIsNone(fila["fase"])
        self.assertEqual(fila["aprobaciones"], 0)

    def test_cientifico_pide_revision_del_sensor_ambiente(self):
        id_solicitud = self._crear("cientifico1", "revision", "cientifico", "sensor_ambiente")
        fila = next(f for f in self._mias("cientifico1") if f["id_solicitud"] == id_solicitud)
        self.assertEqual(fila["dispositivo"], "sensor_ambiente")

    def test_cientifico_pide_acceso_al_critico(self):
        id_solicitud = self._crear("cientifico1", "acceso_sector", "critico", None)
        fila = next(f for f in self._mias("cientifico1") if f["id_solicitud"] == id_solicitud)
        self.assertEqual((fila["tipo"], fila["sector"]), ("acceso_sector", "critico"))
        self.assertIsNone(fila["dispositivo"])

    # Rechazadas

    def test_reglas_al_crear(self):
        casos = [
            ("cientifico pide mantenimiento",
             dict(login="cientifico1", tipo="mantenimiento", sector="cientifico",
                  dispositivo="bomba_agua")),
            ("alta_usuario", dict(login="tech1", tipo="alta_usuario", sector="general",
                                  dispositivo="barrera")),
            ("accion_restringida", dict(login="tech1", tipo="accion_restringida",
                                        sector="general", dispositivo="barrera")),
            ("acceso a su propio sector", dict(login="cientifico1", tipo="acceso_sector",
                                               sector="cientifico", dispositivo=None)),
            ("revision sin dispositivo", dict(login="tech1", tipo="revision",
                                              sector="general", dispositivo=None)),
            ("duración 0", dict(login="tech1", tipo="revision", sector="general",
                                dispositivo="barrera", duracion=0)),
            ("duración 481", dict(login="tech1", tipo="revision", sector="general",
                                  dispositivo="barrera", duracion=481)),
            ("motivo vacío", dict(login="tech1", tipo="revision", sector="general",
                                  dispositivo="barrera", motivo="   ")),
        ]
        antes = {login: self._mias(login) for login in ("tech1", "cientifico1")}
        for nombre, caso in casos:
            with self.subTest(nombre), self.assertRaises(ErrorRegla):
                self._crear(**caso)
        for login, solicitudes in antes.items():
            self.assertEqual(self._mias(login), solicitudes)

    def test_dispositivo_de_otro_sector(self):
        # La barrera es del sector general
        barrera = self._dispositivo("barrera", "general")
        with self._como("cientifico1"), self.assertRaises(ErrorRegla) as error:
            repositorio.crear_solicitud(self.cuentas["cientifico1"]["id_usuario"], "revision",
                                        "normal", "Prueba", self.sectores["cientifico"], 30,
                                        barrera)
        self.assertEqual(str(error.exception), "El dispositivo no es de ese sector")

    def test_acceso_a_un_sector_con_dispositivo(self):
        with self.assertRaises(ErrorRegla) as error:
            self._crear("cientifico1", "acceso_sector", "critico", "turbina")
        self.assertEqual(str(error.exception), "El acceso a un sector no lleva dispositivo")

    # Seguridad

    def test_cuenta_bloqueada_no_crea_nada(self):
        with self.assertRaises(ErrorRegla) as error:
            self._crear(CUENTA_BLOQUEADA[0], "revision", "general", "barrera")
        self.assertEqual(str(error.exception), "No autorizado")

    def test_usuario_de_bd_de_otro_perfil_no_crea_nada(self):
        # a3i_tech con el id de un científico
        antes = self._mias("cientifico1")
        with self.assertRaises(ErrorRegla) as error:
            self._crear("cientifico1", "revision", "cientifico", "sensor_ambiente",
                        perfil="tech")
        self.assertEqual(str(error.exception), "No autorizado")
        self.assertEqual(self._mias("cientifico1"), antes)

    # Ver

    def test_mis_solicitudes_solo_devuelve_las_suyas(self):
        mia = self._crear("tech1", "revision", "general", "camara")
        otra = self._crear("cientifico1", "revision", "cientifico", "caudalimetro")
        de_tech1 = [f["id_solicitud"] for f in self._mias("tech1")]
        de_cientifico1 = [f["id_solicitud"] for f in self._mias("cientifico1")]
        # La más nueva sale primero
        self.assertEqual(de_tech1[0], mia)
        self.assertEqual(de_cientifico1[0], otra)
        self.assertNotIn(otra, de_tech1)
        self.assertNotIn(mia, de_cientifico1)

    # Cancelar

    def test_cancelar_la_propia_pendiente(self):
        id_solicitud = self._crear("tech1", "revision", "general", "barrera")
        self._cancelar("tech1", id_solicitud)
        fila = next(f for f in self._mias("tech1") if f["id_solicitud"] == id_solicitud)
        self.assertEqual(fila["estado"], "cancelada")
        self.assertIsNotNone(fila["fecha_resolucion"])

    def test_cancelar_la_de_otro(self):
        id_solicitud = self._crear("cientifico1", "revision", "cientifico", "caudalimetro")
        with self.assertRaises(ErrorRegla):
            self._cancelar("tech1", id_solicitud)
        fila = next(f for f in self._mias("cientifico1") if f["id_solicitud"] == id_solicitud)
        self.assertEqual(fila["estado"], "pendiente")

    def test_cancelar_una_ya_cancelada(self):
        id_solicitud = self._crear("tech1", "revision", "general", "barrera")
        self._cancelar("tech1", id_solicitud)
        with self.assertRaises(ErrorRegla) as error:
            self._cancelar("tech1", id_solicitud)
        self.assertEqual(str(error.exception), "Solo se pueden cancelar las pendientes")


if __name__ == "__main__":
    unittest.main()
