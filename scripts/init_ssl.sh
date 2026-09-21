#!/usr/bin/env bash
# ============================================================
# Proyecto HV — Inicialización y Gestión de Certificados SSL
# ============================================================
# Uso:
#   ./scripts/init_ssl.sh [staging|production] [dominio] [email]
#
# Ejemplos:
#   ./scripts/init_ssl.sh staging
#   ./scripts/init_ssl.sh production hv.midominio.gov.co admin@midominio.gov.co
# ============================================================

set -e

MODE="${1:-staging}"
DOMAIN="${2:-localhost}"
EMAIL="${3:-admin@example.com}"

SSL_DIR="./nginx/ssl"
mkdir -p "${SSL_DIR}"

echo "============================================================"
echo " Inicializando certificados SSL para Proyecto HV"
echo " Modo: ${MODE} | Dominio: ${DOMAIN}"
echo "============================================================"

# Verificar si ya existen certificados
if [ -f "${SSL_DIR}/fullchain.pem" ] && [ -f "${SSL_DIR}/privkey.pem" ]; then
    echo "[OK] Ya existen certificados SSL en ${SSL_DIR}."
    echo "Si desea regenerarlos, elimine los archivos y vuelva a ejecutar este script."
    exit 0
fi

if [ "${MODE}" = "staging" ] || [ "${DOMAIN}" = "localhost" ]; then
    echo "[INFO] Generando certificado autofirmado para pruebas y arranque inicial..."
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -keyout "${SSL_DIR}/privkey.pem" \
        -out "${SSL_DIR}/fullchain.pem" \
        -subj "/C=CO/ST=Antioquia/L=Medellin/O=Proyecto HV/OU=TI/CN=${DOMAIN}"

    chmod 600 "${SSL_DIR}/privkey.pem"
    chmod 644 "${SSL_DIR}/fullchain.pem"
    echo "[OK] Certificado autofirmado generado exitosamente en ${SSL_DIR}."
    echo "Los contenedores Nginx pueden arrancar de inmediato."
    exit 0
fi

# Modo Producción con Certbot / Let's Encrypt
if [ "${MODE}" = "production" ]; then
    if [ -z "${DOMAIN}" ] || [ "${DOMAIN}" = "localhost" ]; then
        echo "[ERROR] En modo producción debe especificar un dominio público válido."
        echo "Uso: ./scripts/init_ssl.sh production tu-dominio.gov.co tu-email@gov.co"
        exit 1
    fi

    echo "[INFO] 1. Creando certificado temporal para inicio de Nginx..."
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout "${SSL_DIR}/privkey.pem" \
        -out "${SSL_DIR}/fullchain.pem" \
        -subj "/CN=${DOMAIN}"

    echo "[INFO] 2. Levantando Nginx para validación ACME..."
    docker compose -f docker-compose.prod.yml up -d nginx

    echo "[INFO] 3. Solicitando certificado a Let's Encrypt mediante Certbot..."
    docker run --rm \
        -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
        -v "$(pwd)/certbot/www:/var/www/certbot" \
        certbot/certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "${EMAIL}" \
        --agree-tos \
        --no-eff-email \
        -d "${DOMAIN}"

    echo "[INFO] 4. Vinculando certificados oficiales de Let's Encrypt..."
    cp "./certbot/conf/live/${DOMAIN}/fullchain.pem" "${SSL_DIR}/fullchain.pem"
    cp "./certbot/conf/live/${DOMAIN}/privkey.pem" "${SSL_DIR}/privkey.pem"

    echo "[INFO] 5. Recargando Nginx con certificados válidos..."
    docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

    echo "[OK] Certificados Let's Encrypt configurados y renovables automáticamente."
fi
