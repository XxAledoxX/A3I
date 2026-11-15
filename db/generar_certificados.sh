#!/usr/bin/env bash
# Genera una autoridad propia (CA) y el certificado del servidor MariaDB para TLS
# Uso: ./db/generar_certificados.sh
# Los deja en db/certificados/, que no se sube (está en .gitignore)
set -euo pipefail

raiz="$(cd "$(dirname "$0")/.." && pwd)"
carpeta="$raiz/db/certificados"
dias=825

if [[ -f "$carpeta/ca.pem" ]]; then
    echo "Ya hay certificados en $carpeta. Si quieres otros, borra la carpeta antes." >&2
    exit 1
fi

mkdir -p "$carpeta"
chmod 700 "$carpeta"
cd "$carpeta"
# Las claves solo las puede leer su dueño
umask 077

# Autoridad propia: firma el certificado del servidor y la app confía en ella
openssl req -new -newkey rsa:3072 -nodes -subj "/CN=A3I CA local" \
    -keyout ca-key.pem -out ca.csr 2>/dev/null
openssl x509 -req -in ca.csr -signkey ca-key.pem -days "$dias" -sha256 -out ca.pem \
    -extfile <(printf 'basicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\n') \
    2>/dev/null

# Certificado del servidor, válido para localhost y 127.0.0.1
openssl req -new -newkey rsa:3072 -nodes -subj "/CN=localhost" \
    -keyout servidor-key.pem -out servidor.csr 2>/dev/null
openssl x509 -req -in servidor.csr -CA ca.pem -CAkey ca-key.pem \
    -set_serial "0x$(openssl rand -hex 16)" -days "$dias" -sha256 -out servidor.pem \
    -extfile <(printf 'subjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid\n') \
    2>/dev/null

rm ca.csr servidor.csr
chmod 644 ca.pem servidor.pem

openssl verify -CAfile ca.pem servidor.pem

cat <<FIN

Certificados en $carpeta
Siguiente paso: configurar MariaDB (db/README.md, apartado «TLS»).
FIN
