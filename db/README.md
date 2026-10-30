# Base de datos

Para crear o resetear la BD:

1. Copia `.env.example` a `.env` y pon una contraseña en `DB_PASSWORD` (por ejemplo con `openssl rand -hex 24`).
2. Ejecuta `./db/reset_db.sh` y escribe la contraseña de root de MariaDB.

Hay que repetirlo después de cada `git pull` que cambie algo en `db/`.

## Usuarios de prueba

| Usuario | Contraseña | Perfil | Nivel |
|---|---|---|---|
| `cientifico1` | `Cientifico1.Prueba` | Científicos | 2 |
| `seguridad1` | `Seguridad1.Prueba` | Seguridad | 1 |
| `tech1` | `Tech1.Prueba` | Tech | 1 |

## Hash de un usuario nuevo

Las contraseñas se guardan con Argon2id (RF-005), nunca en claro. Para añadir un usuario a `003_datos_prueba.sql`, genera el hash desde la raíz del proyecto y pégalo en `hash_contrasena`:

```
.venv/bin/python -c "from getpass import getpass; from argon2 import PasswordHasher; print(PasswordHasher().hash(getpass('Contraseña: ')))"
```

En Windows, `.venv\Scripts\python` en vez de `.venv/bin/python`. La contraseña se pide sin mostrarla, así no queda en el historial de la terminal. Cada vez sale un hash distinto porque lleva una sal aleatoria; es normal. Apunta la contraseña en la tabla de arriba.
