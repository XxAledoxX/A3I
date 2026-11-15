# A3I

Dashboard de escritorio para una central nuclear (maqueta) con tres perfiles: Científicos, Seguridad y Tech.

Proyecto de Ingeniería I, Universidad Europea, curso 2026-2027.
Equipo: Alejandro Dotor, Arturo Fernández y Aarón Peñafiel.

## Ramas

- `main`: versión estable de cada sprint, con tag.
- `production`: solo recibe de `main`.
- `development`: de aquí salen las ramas de tarea (`AD/RF-004-login`, ...) y aquí vuelven por PR.

Cada rama de tarea lleva su archivo en `tareas/` con el nombre del alumno y la tarea (`tareas/ALEJANDRO_RF-022.txt`).

## Primera instalación

1. **Requisitos:** Python 3.14, MariaDB, `openssl` y `bash`.
2. **Entorno de Python**, desde la raíz del proyecto:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   En Windows: `.venv\Scripts\activate` en vez de `source .venv/bin/activate`.
3. **`.env`:** copia la plantilla y genera las 6 contraseñas con el bucle de [db/README.md](db/README.md).
   ```
   cp .env.example .env
   ```
4. **Certificados y TLS:** genera los certificados y configura MariaDB con ellos, como explica el apartado [TLS de db/README.md](db/README.md#tls). Se hace una vez en cada equipo.
   ```
   ./db/generar_certificados.sh
   ```
5. **Base de datos:**
   ```
   ./db/reset_db.sh
   ```
   En Arch, con `sudo ./db/reset_db.sh`, porque root entra por `unix_socket`: cuando pida la contraseña, pulsa Enter.
6. **Pruebas:**
   ```
   ./tests/ejecutar_tests.sh
   ```
7. **Arrancar la app:**
   ```
   python main.py
   ```
   Los usuarios de prueba y sus contraseñas están en [db/README.md](db/README.md#usuarios-de-prueba).
8. **Lecturas en directo:** en otra terminal, con el entorno activado:
   ```
   python simulador.py
   ```
