#!/usr/bin/env bash
# Borra las BD a3i y a3i_lecturas y las vuelve a crear con los scripts de db/
# Uso: ./db/reset_db.sh (pide la contraseña de root)
set -euo pipefail

raiz="$(cd "$(dirname "$0")/.." && pwd)"
env_file="$raiz/.env"

if [[ ! -f "$env_file" ]]; then
    echo "Falta el .env: copia .env.example a .env y rellena DB_PASSWORD." >&2
    exit 1
fi

password="$(grep -E '^DB_PASSWORD=' "$env_file" | tail -n 1 | cut -d '=' -f 2- | tr -d '\r')"

if [[ ! "$password" =~ ^[A-Za-z0-9._-]{12,}$ ]]; then
    echo "DB_PASSWORD debe tener al menos 12 caracteres: letras, números, '.', '_' o '-'." >&2
    exit 1
fi

scripts=("$raiz"/db/[0-9][0-9][0-9]_*.sql)

# La contraseña se pasa por la entrada estándar para que no salga en ps
{
    printf "SET @a3i_app_password = '%s';\n" "$password"
    # Primero a3i_lecturas: su FK a a3i.variable impide borrar a3i
    echo "DROP DATABASE IF EXISTS a3i_lecturas;"
    cat "${scripts[@]}"
} | mariadb -u root -p
