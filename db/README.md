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
