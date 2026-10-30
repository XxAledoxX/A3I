"""RF-014: el SQL solo está en repositorio.py y siempre es texto fijo.

No ejecuta la aplicación: lee el código con ast, así que no necesita BD.
Avisa de consultas nuevas que se salten las normas de repositorio.py.
"""

import ast
import unittest
from pathlib import Path

CARPETA_APP = Path(__file__).resolve().parent.parent / "app"
REPOSITORIO = CARPETA_APP / "model" / "repositorio.py"

# Funciones de repositorio.py que reciben el SQL como primer argumento.
# Son las únicas que pueden llamar a cursor.execute
FUNCIONES_SQL = {"_consultar_uno", "_ejecutar"}


def _leer(ruta: Path) -> ast.Module:
    return ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))


def _es_execute(nodo: ast.AST) -> bool:
    return (
        isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and nodo.func.attr in ("execute", "executemany")
    )


def _textos_fijos(funcion: ast.FunctionDef) -> set[str]:
    """Variables de la función a las que solo se asigna texto fijo."""
    fijos, otros = set(), set()
    for nodo in ast.walk(funcion):
        if isinstance(nodo, (ast.Assign, ast.AnnAssign)):
            destinos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
            es_texto = isinstance(nodo.value, ast.Constant) and isinstance(
                nodo.value.value, str
            )
            for destino in destinos:
                if isinstance(destino, ast.Name):
                    (fijos if es_texto else otros).add(destino.id)
        elif isinstance(nodo, ast.AugAssign) and isinstance(nodo.target, ast.Name):
            # sql += ... ya no es texto fijo
            otros.add(nodo.target.id)
    return fijos - otros


def errores_fuera_del_repositorio(arbol: ast.Module, nombre: str) -> list[str]:
    """pymysql o execute en un archivo que no es repositorio.py."""
    errores = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module or ""]
        else:
            modulos = []
        if any(m.split(".")[0] == "pymysql" for m in modulos):
            errores.append(f"{nombre}:{nodo.lineno} importa pymysql")
        if _es_execute(nodo):
            errores.append(f"{nombre}:{nodo.lineno} ejecuta SQL")
    return errores


def errores_sql_no_fijo(arbol: ast.Module, nombre: str) -> list[str]:
    """SQL construido con variables, o execute fuera de FUNCIONES_SQL."""
    errores = []
    for funcion in ast.walk(arbol):
        if not isinstance(funcion, ast.FunctionDef):
            continue
        fijos = _textos_fijos(funcion)
        for nodo in ast.walk(funcion):
            if _es_execute(nodo) and funcion.name not in FUNCIONES_SQL:
                errores.append(
                    f"{nombre}:{nodo.lineno} execute fuera de {sorted(FUNCIONES_SQL)}"
                )
            if not (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Name)
                and nodo.func.id in FUNCIONES_SQL
            ):
                continue
            sql = nodo.args[0] if nodo.args else None
            es_fijo = (
                isinstance(sql, ast.Constant) and isinstance(sql.value, str)
            ) or (isinstance(sql, ast.Name) and sql.id in fijos)
            if not es_fijo:
                errores.append(
                    f"{nombre}:{nodo.lineno} el SQL de {nodo.func.id} no es texto fijo"
                )
    return errores


class PruebasSqlFijo(unittest.TestCase):

    def test_no_hay_sql_fuera_del_repositorio(self):
        errores = []
        for ruta in sorted(CARPETA_APP.rglob("*.py")):
            if ruta != REPOSITORIO:
                nombre = str(ruta.relative_to(CARPETA_APP.parent))
                errores += errores_fuera_del_repositorio(_leer(ruta), nombre)
        self.assertEqual(errores, [])

    def test_sql_del_repositorio_es_texto_fijo(self):
        nombre = str(REPOSITORIO.relative_to(CARPETA_APP.parent))
        self.assertEqual(errores_sql_no_fijo(_leer(REPOSITORIO), nombre), [])


if __name__ == "__main__":
    unittest.main()
