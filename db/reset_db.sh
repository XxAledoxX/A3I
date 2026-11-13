#!/usr/bin/env bash
# Borra las BD a3i y a3i_lecturas y las vuelve a crear con los scripts de db/
# Uso: ./db/reset_db.sh (pide la contraseña de root)
set -euo pipefail

raiz="$(cd "$(dirname "$0")/.." && pwd)"
env_file="$raiz/.env"

if [[ ! -f "$env_file" ]]; then
    echo "Falta el .env: copia .env.example a .env y rellena las contraseñas." >&2
    exit 1
fi

# Lee una contraseña del .env y comprueba su formato
leer_password() {
    local valor
    valor="$(grep -E "^$1=" "$env_file" | tail -n 1 | cut -d '=' -f 2- | tr -d '\r')"
    if [[ ! "$valor" =~ ^[A-Za-z0-9._-]{12,}$ ]]; then
        echo "$1 debe tener al menos 12 caracteres: letras, números, '.', '_' o '-'." >&2
        exit 1
    fi
    printf '%s' "$valor"
}

password="$(leer_password DB_PASSWORD)"
password_login="$(leer_password DB_PASSWORD_LOGIN)"
password_cientificos="$(leer_password DB_PASSWORD_CIENTIFICOS)"
password_seguridad="$(leer_password DB_PASSWORD_SEGURIDAD)"
password_tech="$(leer_password DB_PASSWORD_TECH)"

scripts=("$raiz"/db/[0-9][0-9][0-9]_*.sql)

# Las contraseñas se pasan por la entrada estándar para que no salgan en ps
{
    printf "SET @a3i_app_password = '%s';\n" "$password"
    printf "SET @a3i_login_password = '%s';\n" "$password_login"
    printf "SET @a3i_cientificos_password = '%s';\n" "$password_cientificos"
    printf "SET @a3i_seguridad_password = '%s';\n" "$password_seguridad"
    printf "SET @a3i_tech_password = '%s';\n" "$password_tech"
    # Primero a3i_lecturas: su FK a a3i.variable impide borrar a3i
    echo "DROP DATABASE IF EXISTS a3i_lecturas;"
    cat "${scripts[@]}"
} | mariadb -u root -p
