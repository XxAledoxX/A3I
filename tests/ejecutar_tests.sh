#!/usr/bin/env bash
# Ejecuta las pruebas de tests/ con el Python del .venv
# Uso: ./tests/ejecutar_tests.sh                         (todas)
#      ./tests/ejecutar_tests.sh tests.test_rf014_inyeccion   (una en concreto)
set -euo pipefail

raiz="$(cd "$(dirname "$0")/.." && pwd)"
cd "$raiz"

if [[ -x .venv/bin/python ]]; then
    python=.venv/bin/python
elif [[ -x .venv/Scripts/python.exe ]]; then
    python=.venv/Scripts/python.exe
else
    echo "Falta el .venv: créalo e instala requirements.txt (ver README)." >&2
    exit 1
fi

if [[ ! -f .env ]]; then
    echo "Aviso: no hay .env, las pruebas con BD se van a saltar." >&2
fi

"$python" -m unittest -v "$@"
