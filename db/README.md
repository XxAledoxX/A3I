# Base de datos

Para crear o resetear la BD:

1. Copia `.env.example` a `.env` y pon una contraseña distinta en cada `DB_PASSWORD...` (por ejemplo con `openssl rand -hex 24`).

   Para generarlas todas de una vez:

   ```
   for v in DB_PASSWORD DB_PASSWORD_LOGIN DB_PASSWORD_CIENTIFICOS DB_PASSWORD_SEGURIDAD DB_PASSWORD_TECH; do
       sed -i.bak "s/^$v=.*/$v=$(openssl rand -hex 24)/" .env
   done
   rm .env.bak
   ```

   Si ya tenías un `.env`, copia antes las líneas nuevas de `.env.example`: el bucle solo rellena las que existen.
2. Ejecuta `./db/reset_db.sh` y escribe la contraseña de root de MariaDB.

Hay que repetirlo después de cada `git pull` que cambie algo en `db/`.

## Usuarios de BD

La aplicación no lee las tablas: solo ejecuta procedimientos (`db/007_control_acceso.sql`).

| Usuario | Para qué | Puede ejecutar |
|---|---|---|
| `a3i_login` | Iniciar sesión | `buscar_usuario`, `registrar_fallo`, `actualizar_intentos`, `actualizar_hash` |
| `a3i_cientificos`, `a3i_seguridad`, `a3i_tech` | Datos tras el login, según el perfil | `ultimas_lecturas`, `estado_actuadores`, `estado_equipos` |

Los procedimientos de datos solo devuelven algo si el usuario de BD que llama es el del perfil del usuario: desde DBeaver con root salen vacíos.

## Usuarios de prueba

| Usuario | Contraseña | Perfil | Rango | Nivel | Sector |
|---|---|---|---|---|---|
| `cientifico1` | `Cientifico1.Prueba` | Científicos | Empleado | 2 | cientifico |
| `seguridad1` | `Seguridad1.Prueba` | Seguridad | Empleado | 1 | general |
| `tech1` | `Tech1.Prueba` | Tech | Empleado | 1 | general |
| `cientifico2` | `Cientifico2.Prueba` | Científicos | Empleado | 3 | critico |
| `jefesector_cien` | `Jefesector_cien.Prueba` | Científicos | Jefe de sector | 3 | cientifico |
| `subjefe_cien` | `Subjefe_cien.Prueba` | Científicos | Subjefe de perfil | 2 | cientifico |
| `jefe_cien` | `Jefe_cien.Prueba` | Científicos | Jefe de perfil | 3 | critico |
| `jefesector_seg` | `Jefesector_seg.Prueba` | Seguridad | Jefe de sector | 2 | general |
| `subjefe_seg` | `Subjefe_seg.Prueba` | Seguridad | Subjefe de perfil | 4 | general |
| `jefe_seg` | `Jefe_seg.Prueba` | Seguridad | Jefe de perfil | 4 | general |
| `tech2` | `Tech2.Prueba` | Tech | Empleado | 1 | critico |
| `subjefe_tech` | `Subjefe_tech.Prueba` | Tech | Subjefe de perfil | 2 | cientifico |
| `jefe_tech` | `Jefe_tech.Prueba` | Tech | Jefe de perfil | 3 | critico |

## Hash de un usuario nuevo

Las contraseñas se guardan con Argon2id (RF-005), nunca en claro. Para añadir un usuario a `003_datos_prueba.sql`, genera el hash desde la raíz del proyecto y pégalo en `hash_contrasena`:

```
.venv/bin/python -c "from getpass import getpass; from argon2 import PasswordHasher; print(PasswordHasher().hash(getpass('Contraseña: ')))"
```

En Windows, `.venv\Scripts\python` en vez de `.venv/bin/python`. La contraseña se pide sin mostrarla, así no queda en el historial de la terminal. Cada vez sale un hash distinto porque lleva una sal aleatoria; es normal. Apunta la contraseña en la tabla de arriba.

## TLS

La app solo se conecta cifrado (RF-016): comprueba que el certificado del servidor lo firma nuestra autoridad propia (CA) y que es para `127.0.0.1`. Los usuarios de BD de la app tienen `REQUIRE SSL` (`db/008_tls.sql`), y el reset falla con un aviso si MariaDB no tiene TLS configurado. Hay que hacerlo una vez en cada equipo:

1. Genera los certificados (quedan en `db/certificados/`, que no se sube):

   ```
   ./db/generar_certificados.sh
   ```

2. Configura MariaDB con ellos y reinícialo.

   **Arch.** MariaDB se ejecuta como el usuario `mysql`, que no puede leer tu carpeta personal, así que se copian a `/etc/my.cnf.d/certificados/`. La configuración va en un archivo propio dentro de `/etc/my.cnf.d/` (es lo mismo que añadirla a `server.cnf`):

   ```
   sudo install -d -o mysql -g mysql -m 750 /etc/my.cnf.d/certificados
   sudo install -o mysql -g mysql -m 644 db/certificados/ca.pem db/certificados/servidor.pem /etc/my.cnf.d/certificados/
   sudo install -o mysql -g mysql -m 600 db/certificados/servidor-key.pem /etc/my.cnf.d/certificados/
   printf '[mariadb]\nssl_ca = /etc/my.cnf.d/certificados/ca.pem\nssl_cert = /etc/my.cnf.d/certificados/servidor.pem\nssl_key = /etc/my.cnf.d/certificados/servidor-key.pem\ntls_version = TLSv1.2,TLSv1.3\n' | sudo tee /etc/my.cnf.d/a3i-tls.cnf
   sudo systemctl restart mariadb
   ```

   **macOS (Homebrew).** MariaDB se ejecuta con tu usuario y puede leer los certificados donde están. Desde la raíz del proyecto (en un Mac con Intel el archivo es `/usr/local/etc/my.cnf`):

   ```
   printf '\n[mariadb]\nssl_ca = %s/db/certificados/ca.pem\nssl_cert = %s/db/certificados/servidor.pem\nssl_key = %s/db/certificados/servidor-key.pem\ntls_version = TLSv1.2,TLSv1.3\n' "$PWD" "$PWD" "$PWD" >> /opt/homebrew/etc/my.cnf
   brew services restart mariadb
   ```

3. Comprueba que MariaDB ha cargado el certificado (debe salir la ruta de `servidor.pem`):

   ```
   mariadb -u root -p -e "SELECT @@ssl_cert, @@tls_version"
   ```

   Si entras sin contraseña por `unix_socket` (como en el Mac de Alejandro), quita `-u root -p` aquí y en el reset: root no necesita TLS por el socket, solo los usuarios de la app.

4. Añade al `.env` la línea `DB_SSL_CA=db/certificados/ca.pem` (está en `.env.example`), ejecuta el reset y las pruebas.
