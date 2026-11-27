"""RF-076: aprobar y rechazar solicitudes con la regla N+1.

Usan la BD de prueba (./db/reset_db.sh) y se saltan si MariaDB no está
disponible. Van en una transacción que se deshace al acabar.

Quien crea y quien decide usan el mismo usuario de BD: en la misma
transacción, otra conexión se quedaría esperando a la que creó la fila.

    python -m unittest -v tests.test_rf076_aprobaciones
"""

import unittest
from datetime import datetime, timedelta
from unittest import mock

from app.model import repositorio
from app.model.repositorio import ErrorRegla
from tests.bd import LOGINS_PRUEBA, PruebaConTransaccion, hay_bd

COLUMNAS = {"id_solicitud", "tipo", "prioridad", "solicitante", "sector", "dispositivo",
            "motivo", "duracion_min", "fecha_creacion"}


@unittest.skipUnless(hay_bd(), "MariaDB no disponible")
class PruebasAprobaciones(PruebaConTransaccion):

    def setUp(self):
        super().setUp()
        self.cuentas = {login: repositorio.buscar_por_login(login) for login in LOGINS_PRUEBA}
        with self._como("tech1"):
            self.sectores = {s["nombre"]: s["id_sector"]
                             for s in repositorio.sectores(self._id("tech1"))}

    def _id(self, login: str) -> int:
        return self.cuentas[login]["id_usuario"]

    def _como(self, login: str, perfil: str | None = None):
        return mock.patch.object(repositorio, "_perfil_conectado",
                                 perfil or self.cuentas[login]["perfil"])

    def _pedir_acceso(self, login: str, sector: str, prioridad: str = "normal") -> int:
        with self._como(login):
            return repositorio.crear_solicitud(self._id(login), "acceso_sector", prioridad,
                                               "Prueba", self.sectores[sector], 30, None)

    def _pedir_revision(self, login: str, sector: str, dispositivo: str) -> int:
        with self._como(login):
            filas = repositorio.dispositivos_sector(self._id(login), self.sectores[sector])
            id_dispositivo = next(f["id_dispositivo"] for f in filas if f["nombre"] == dispositivo)
            return repositorio.crear_solicitud(self._id(login), "revision", "normal", "Prueba",
                                               self.sectores[sector], 30, id_dispositivo)

    def _por_aprobar(self, login: str) -> list[int]:
        with self._como(login):
            return [f["id_solicitud"] for f in repositorio.por_aprobar(self._id(login))]

    def _aprobar(self, login: str, id_solicitud: int, comentario: str = "") -> None:
        with self._como(login):
            repositorio.aprobar_solicitud(self._id(login), id_solicitud, comentario)

    def _rechazar(self, login: str, id_solicitud: int) -> None:
        with self._como(login):
            repositorio.rechazar_solicitud(self._id(login), id_solicitud, "No procede")

    def _solicitud(self, login: str, id_solicitud: int) -> dict:
        with self._como(login):
            filas = repositorio.mis_solicitudes(self._id(login))
        return next(f for f in filas if f["id_solicitud"] == id_solicitud)

    # Regla N+1

    def test_acceso_al_critico_lo_aprueba_seguridad_con_nivel_4(self):
        id_solicitud = self._pedir_acceso("seguridad1", "critico")
        for login in ("jefe_seg", "subjefe_seg"):
            with self.subTest(login=login):
                self.assertIn(id_solicitud, self._por_aprobar(login))
        # jefesector_seg tiene nivel 2 y jefe_cien es de otro perfil
        for login in ("jefesector_seg", "jefe_cien", "jefesector_cien", "jefe_tech"):
            with self.subTest(login=login):
                self.assertNotIn(id_solicitud, self._por_aprobar(login))

    def test_acceso_al_cientifico_lo_aprueba_su_jefe_de_sector(self):
        id_solicitud = self._pedir_acceso("cientifico2", "cientifico")
        self.assertIn(id_solicitud, self._por_aprobar("jefesector_cien"))
        # subjefe_cien es del sector pero tiene nivel 2; jefe_cien es jefe de perfil
        for login in ("subjefe_cien", "jefe_cien", "jefe_seg", "jefesector_seg"):
            with self.subTest(login=login):
                self.assertNotIn(id_solicitud, self._por_aprobar(login))

    def test_acceso_al_general_lo_aprueba_el_jefe_de_sector_de_seguridad(self):
        id_solicitud = self._pedir_acceso("cientifico1", "general")
        self.assertIn(id_solicitud, self._por_aprobar("jefesector_seg"))
        for login in ("jefe_seg", "subjefe_seg", "jefesector_cien", "jefe_tech"):
            with self.subTest(login=login):
                self.assertNotIn(id_solicitud, self._por_aprobar(login))

    def test_tipo_sin_regla_no_lo_aprueba_nadie(self):
        id_solicitud = self._pedir_revision("tech1", "general", "camara")
        for login in ("jefe_tech", "subjefe_tech"):
            with self.subTest(login=login):
                self.assertNotIn(id_solicitud, self._por_aprobar(login))
        with self.assertRaises(ErrorRegla) as error:
            self._aprobar("jefe_tech", id_solicitud)
        self.assertEqual(str(error.exception), "Aún no está decidido quién aprueba este tipo")

    # Aprobar y rechazar

    def test_aprobar(self):
        id_solicitud = self._pedir_acceso("seguridad1", "critico")
        antes = datetime.now().replace(microsecond=0)
        self._aprobar("subjefe_seg", id_solicitud, "Revisión del detector")
        fila = self._solicitud("seguridad1", id_solicitud)
        self.assertEqual((fila["estado"], fila["fase"]), ("aceptada", "autorizada"))
        self.assertEqual(fila["aprobaciones"], 1)
        # Caduca a los 60 min de plazo_inicio_min si no se empieza
        caducidad = fila["fecha_caducidad"] - fila["fecha_resolucion"]
        self.assertEqual(caducidad, timedelta(minutes=60))
        self.assertGreaterEqual(fila["fecha_resolucion"], antes)
        self.assertNotIn(id_solicitud, self._por_aprobar("jefe_seg"))

    def test_rechazar(self):
        id_solicitud = self._pedir_acceso("seguridad1", "critico")
        self._rechazar("jefe_seg", id_solicitud)
        fila = self._solicitud("seguridad1", id_solicitud)
        self.assertEqual((fila["estado"], fila["fase"]), ("rechazada", None))
        self.assertIsNone(fila["fecha_caducidad"])
        self.assertIsNotNone(fila["fecha_resolucion"])
        self.assertEqual(fila["aprobaciones"], 0)

    def test_por_aprobar_columnas_y_orden(self):
        normal = self._pedir_acceso("seguridad1", "critico")
        alta = self._pedir_acceso("jefesector_seg", "critico", prioridad="alta")
        filas = []
        with self._como("jefe_seg"):
            filas = [f for f in repositorio.por_aprobar(self._id("jefe_seg"))
                     if f["id_solicitud"] in (normal, alta)]
        self.assertEqual(set(filas[0]), COLUMNAS)
        self.assertEqual([f["id_solicitud"] for f in filas], [alta, normal])
        self.assertEqual(filas[0]["solicitante"], "Raúl Castillo")

    # Lo que no se puede hacer

    def test_nadie_aprueba_la_suya(self):
        # subjefe_seg tendría autoridad sobre el crítico, pero la pide él
        id_solicitud = self._pedir_acceso("subjefe_seg", "critico")
        self.assertNotIn(id_solicitud, self._por_aprobar("subjefe_seg"))
        with self.assertRaises(ErrorRegla) as error:
            self._aprobar("subjefe_seg", id_solicitud)
        self.assertEqual(str(error.exception), "No puedes decidir sobre tu propia solicitud")
        self.assertEqual(self._solicitud("subjefe_seg", id_solicitud)["estado"], "pendiente")

    def test_sin_autoridad(self):
        id_solicitud = self._pedir_acceso("seguridad1", "critico")
        for login in ("jefesector_seg", "seguridad1"):
            with self.subTest(login=login):
                with self.assertRaises(ErrorRegla):
                    self._aprobar(login, id_solicitud)
        self.assertEqual(self._solicitud("seguridad1", id_solicitud)["estado"], "pendiente")

    def test_no_se_decide_dos_veces(self):
        id_solicitud = self._pedir_acceso("seguridad1", "critico")
        self._aprobar("subjefe_seg", id_solicitud)
        with self.assertRaises(ErrorRegla) as error:
            self._rechazar("jefe_seg", id_solicitud)
        self.assertEqual(str(error.exception), "La solicitud ya no está pendiente")
        self.assertEqual(self._solicitud("seguridad1", id_solicitud)["estado"], "aceptada")

    def test_cancelada_no_se_aprueba(self):
        id_solicitud = self._pedir_acceso("seguridad1", "critico")
        with self._como("seguridad1"):
            repositorio.cancelar_solicitud(self._id("seguridad1"), id_solicitud)
        self.assertNotIn(id_solicitud, self._por_aprobar("jefe_seg"))
        with self.assertRaises(ErrorRegla):
            self._aprobar("jefe_seg", id_solicitud)

    def test_solicitud_que_no_existe(self):
        with self.assertRaises(ErrorRegla) as error:
            self._aprobar("jefe_seg", 999999)
        self.assertEqual(str(error.exception), "La solicitud no existe")

    def test_decision_no_valida(self):
        id_solicitud = self._pedir_acceso("seguridad1", "critico")
        with self._como("jefe_seg"), self.assertRaises(ErrorRegla):
            repositorio._decidir(self._id("jefe_seg"), id_solicitud, "pendiente", "")

    def test_usuario_de_bd_de_otro_perfil(self):
        id_solicitud = self._pedir_acceso("seguridad1", "critico")
        with self._como("jefe_seg", "tech"):
            self.assertEqual(repositorio.por_aprobar(self._id("jefe_seg")), [])
            with self.assertRaises(ErrorRegla) as error:
                repositorio.aprobar_solicitud(self._id("jefe_seg"), id_solicitud)
        self.assertEqual(str(error.exception), "No autorizado")

    def test_login_no_puede_aprobar(self):
        with self.assertRaises(repositorio.ErrorBaseDatos):
            repositorio._ejecutar("CALL decidir_solicitud(%s, %s, %s, %s)",
                                  (self._id("jefe_seg"), 1, "aceptada", ""),
                                  repositorio._credenciales_login())


if __name__ == "__main__":
    unittest.main()
