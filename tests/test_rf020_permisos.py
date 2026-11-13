"""RF-020: pruebas de permisos por perfil, nivel y sector.

Llama a los procedimientos de db/007_control_acceso.sql con cada usuario de
prueba de db/README.md y comprueba lo que dice la tabla de ejemplos de
Assets/Models/Reglas-acceso.pdf. También comprueba que los usuarios de BD
de la app no pueden leer ni cambiar tablas. Se saltan si MariaDB no está
disponible; las de lecturas, además, si todavía no hay lecturas (RF-029).

    python -m unittest -v tests.test_rf020_permisos
"""

import unittest

import pymysql

from app import config
from app.model import repositorio

# Dispositivos y variables de cada sector (db/005_datos_planta.sql)
GENERAL = {"barrera", "camara"}
CIENTIFICO = {"sensor_ambiente", "sensor_aire", "caudalimetro", "bomba_agua", "humidificador"}
CRITICO = {"sensor_interior", "detector_llama", "turbina"}

ACTUADORES_GENERAL = {"barrera", "camara"}
ACTUADORES_CIENTIFICO = {"bomba_agua", "humidificador"}
ACTUADORES_CRITICO = {"turbina"}

VARIABLES_CIENTIFICO = {"temperatura_ambiente", "humedad_ambiente", "calidad_aire", "caudal"}
VARIABLES_CRITICO = {"temperatura_interior", "humedad_interior"}
LLAMA = {"llama"}  # visible para todos

# login: (perfil, variables, actuadores, equipos que ve)
ESPERADO = {
    "cientifico1": ("cientificos", VARIABLES_CIENTIFICO | LLAMA, ACTUADORES_CIENTIFICO, set()),
    "cientifico2": ("cientificos", VARIABLES_CRITICO | LLAMA, ACTUADORES_CRITICO, set()),
    "jefesector_cien": ("cientificos", VARIABLES_CIENTIFICO | LLAMA, ACTUADORES_CIENTIFICO, set()),
    "subjefe_cien": ("cientificos", VARIABLES_CIENTIFICO | LLAMA, ACTUADORES_CIENTIFICO, set()),
    "jefe_cien": ("cientificos", VARIABLES_CIENTIFICO | VARIABLES_CRITICO | LLAMA,
                  ACTUADORES_CIENTIFICO | ACTUADORES_CRITICO, set()),
    "seguridad1": ("seguridad", LLAMA, ACTUADORES_GENERAL, set()),
    "jefesector_seg": ("seguridad", LLAMA, ACTUADORES_GENERAL, set()),
    "subjefe_seg": ("seguridad", LLAMA, ACTUADORES_GENERAL, set()),
    "jefe_seg": ("seguridad", LLAMA, ACTUADORES_GENERAL, set()),
    "tech1": ("tech", LLAMA, set(), GENERAL),
    "tech2": ("tech", LLAMA, set(), CRITICO),
    "subjefe_tech": ("tech", LLAMA, set(), GENERAL | CIENTIFICO),
    "jefe_tech": ("tech", LLAMA, set(), GENERAL | CIENTIFICO | CRITICO),
}

PROCEDIMIENTOS_LOGIN = {
    "buscar_usuario": ("tech1",),
    "registrar_fallo": ("noexiste", 5),
    "actualizar_intentos": (0, 0),
    "actualizar_hash": (0, "x"),
}
PROCEDIMIENTOS_DATOS = ("ultimas_lecturas", "estado_actuadores", "estado_equipos")

# Consultas directas que ningún usuario de la app puede hacer
CONSULTAS_PROHIBIDAS = (
    "SELECT * FROM a3i.usuario",
    "SELECT * FROM a3i.sector",
    "SELECT * FROM a3i.dispositivo",
    "SELECT * FROM a3i.variable",
    "SELECT * FROM a3i_lecturas.lectura",
    "UPDATE a3i.usuario SET estado = 'activo'",
    "UPDATE a3i.actuador SET consigna = 100",
    "DELETE FROM a3i_lecturas.lectura",
)

# Errores de MariaDB por falta de permisos
ERRORES_PERMISO = {1044, 1142, 1143, 1370}


def _credenciales(perfil: str) -> tuple[str, str]:
    return config.USUARIOS_PERFIL[perfil]


def _usuarios_bd() -> dict[str, tuple[str, str]]:
    usuarios = {config.DB_USUARIO_LOGIN: repositorio._credenciales_login()}
    usuarios.update({u: (u, c) for u, c in config.USUARIOS_PERFIL.values()})
    return usuarios


def _hay_bd() -> bool:
    try:
        for credenciales in _usuarios_bd().values():
            repositorio._conectar(*credenciales).close()
        return True
    except pymysql.Error:
        return False


def _llamar(procedimiento: str, id_usuario: int, perfil: str) -> list[dict]:
    # El nombre sale de PROCEDIMIENTOS_DATOS, una lista fija
    sql = {
        "ultimas_lecturas": "CALL ultimas_lecturas(%s)",
        "estado_actuadores": "CALL estado_actuadores(%s)",
        "estado_equipos": "CALL estado_equipos(%s)",
    }[procedimiento]
    return repositorio._consultar_todos(sql, (id_usuario,), _credenciales(perfil))


def _ejecutar_directo(credenciales: tuple[str, str], sql: str, parametros: tuple = ()):
    # Los nombres de procedimiento que llegan aquí salen de listas fijas de este archivo
    with repositorio._conectar(*credenciales) as conexion, conexion.cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.fetchall()


@unittest.skipUnless(_hay_bd(), "MariaDB no disponible o faltan los usuarios de RF-013")
class PruebasBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ids = {
            login: repositorio.buscar_por_login(login)["id_usuario"] for login in ESPERADO
        }

    def _nombres(self, procedimiento: str, login: str, perfil: str | None = None,
                 columna: str = "nombre") -> set[str]:
        perfil = perfil or ESPERADO[login][0]
        return {fila[columna] for fila in _llamar(procedimiento, self.ids[login], perfil)}


class PruebasVisibilidad(PruebasBase):
    """La tabla de ejemplos de Reglas-acceso.pdf, usuario por usuario."""

    def test_estado_actuadores(self):
        for login, (_, _, actuadores, _) in ESPERADO.items():
            with self.subTest(login=login):
                self.assertEqual(self._nombres("estado_actuadores", login), actuadores)

    def test_estado_equipos(self):
        for login, (_, _, _, equipos) in ESPERADO.items():
            with self.subTest(login=login):
                self.assertEqual(self._nombres("estado_equipos", login), equipos)

    def test_columnas_de_estado_actuadores(self):
        fila = _llamar("estado_actuadores", self.ids["seguridad1"], "seguridad")[0]
        self.assertEqual(set(fila), {"nombre", "sector", "posicion", "movimiento", "estado"})

    def test_columnas_de_estado_equipos(self):
        fila = _llamar("estado_equipos", self.ids["tech1"], "tech")[0]
        self.assertEqual(set(fila), {"nombre", "sector", "estado"})

    def test_sector_de_cada_dispositivo(self):
        filas = _llamar("estado_equipos", self.ids["jefe_tech"], "tech")
        sectores = {fila["nombre"]: fila["sector"] for fila in filas}
        for nombres, sector in ((GENERAL, "general"), (CIENTIFICO, "cientifico"),
                                (CRITICO, "critico")):
            for nombre in nombres:
                self.assertEqual(sectores[nombre], sector)


class PruebasLecturas(PruebasBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # jefe_cien ve las siete variables: si no salen todas, no hay lecturas
        todas = VARIABLES_CIENTIFICO | VARIABLES_CRITICO | LLAMA
        filas = _llamar("ultimas_lecturas", cls.ids["jefe_cien"], "cientificos")
        if {fila["variable"] for fila in filas} != todas:
            raise unittest.SkipTest("Sin lecturas: falta el histórico (006, RF-029)")

    def test_ultimas_lecturas(self):
        for login, (_, variables, _, _) in ESPERADO.items():
            with self.subTest(login=login):
                self.assertEqual(
                    self._nombres("ultimas_lecturas", login, columna="variable"), variables
                )

    def test_una_lectura_por_variable(self):
        filas = _llamar("ultimas_lecturas", self.ids["jefe_cien"], "cientificos")
        variables = [fila["variable"] for fila in filas]
        self.assertEqual(len(variables), len(set(variables)))

    def test_columnas_de_ultimas_lecturas(self):
        fila = _llamar("ultimas_lecturas", self.ids["cientifico1"], "cientificos")[0]
        self.assertEqual(set(fila), {"variable", "unidad", "valor", "fecha_hora",
                                     "minimo_normal", "maximo_normal", "sector"})


class PruebasSuplantacion(PruebasBase):
    """Con el usuario de BD de otro perfil, o un id raro, no sale nada."""

    def test_otro_perfil_no_ve_nada(self):
        for login, (perfil, _, _, _) in ESPERADO.items():
            for otro in config.USUARIOS_PERFIL:
                if otro == perfil:
                    continue
                for procedimiento in PROCEDIMIENTOS_DATOS:
                    with self.subTest(login=login, usuario_bd=otro, procedimiento=procedimiento):
                        self.assertEqual(_llamar(procedimiento, self.ids[login], otro), [])

    def test_id_inexistente_no_ve_nada(self):
        for perfil in config.USUARIOS_PERFIL:
            for procedimiento in PROCEDIMIENTOS_DATOS:
                with self.subTest(perfil=perfil, procedimiento=procedimiento):
                    self.assertEqual(_llamar(procedimiento, 999999, perfil), [])

    def test_cuenta_bloqueada_no_ve_nada(self):
        login = "tech1"
        try:
            for _ in range(config.MAX_INTENTOS_FALLIDOS):
                repositorio.registrar_fallo(login, config.MAX_INTENTOS_FALLIDOS)
            self.assertEqual(repositorio.buscar_por_login(login)["estado"], "bloqueado")
            self.assertEqual(_llamar("estado_equipos", self.ids[login], "tech"), [])
        finally:
            # a3i_app (Sprint 1) sigue pudiendo cambiar el estado: solo para dejarlo como estaba
            with repositorio._conectar() as conexion, conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE usuario SET intentos_fallidos = 0, estado = 'activo' WHERE login = %s",
                    (login,),
                )


class PruebasPermisosBD(PruebasBase):
    """Los usuarios de BD de la app solo pueden ejecutar sus procedimientos."""

    def test_no_pueden_leer_ni_cambiar_tablas(self):
        for usuario, credenciales in _usuarios_bd().items():
            for sql in CONSULTAS_PROHIBIDAS:
                with self.subTest(usuario=usuario, sql=sql):
                    with self.assertRaises(pymysql.Error) as error:
                        _ejecutar_directo(credenciales, sql)
                    self.assertIn(error.exception.args[0], ERRORES_PERMISO)

    def test_login_no_puede_pedir_datos(self):
        for procedimiento in PROCEDIMIENTOS_DATOS:
            with self.subTest(procedimiento=procedimiento):
                with self.assertRaises(pymysql.Error) as error:
                    _ejecutar_directo(repositorio._credenciales_login(),
                                      f"CALL {procedimiento}(%s)", (self.ids["jefe_tech"],))
                self.assertIn(error.exception.args[0], ERRORES_PERMISO)

    def test_perfiles_no_pueden_usar_el_login(self):
        for perfil in config.USUARIOS_PERFIL:
            for procedimiento, parametros in PROCEDIMIENTOS_LOGIN.items():
                marcas = ", ".join(["%s"] * len(parametros))
                with self.subTest(perfil=perfil, procedimiento=procedimiento):
                    with self.assertRaises(pymysql.Error) as error:
                        _ejecutar_directo(_credenciales(perfil),
                                          f"CALL {procedimiento}({marcas})", parametros)
                    self.assertIn(error.exception.args[0], ERRORES_PERMISO)

    def test_solo_tienen_permiso_de_ejecutar(self):
        for usuario, credenciales in _usuarios_bd().items():
            with self.subTest(usuario=usuario):
                permisos = _ejecutar_directo(credenciales, "SHOW GRANTS")
                for fila in permisos:
                    permiso = next(iter(fila.values()))
                    if permiso.startswith("GRANT USAGE ON *.*"):
                        continue
                    # Los de PUBLIC son de la instalación de MariaDB, no de la app
                    if permiso.endswith("TO PUBLIC"):
                        continue
                    self.assertRegex(permiso, r"^GRANT EXECUTE ON PROCEDURE `a3i`\.")


if __name__ == "__main__":
    unittest.main()
