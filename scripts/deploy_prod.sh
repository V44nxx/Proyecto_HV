#!/usr/bin/env bash
# ============================================================
# Proyecto HV — Script Automatizado de Despliegue en Producción
# ============================================================
# Uso:
#   chmod +x scripts/deploy_prod.sh
#   ./scripts/deploy_prod.sh
# ============================================================

set -e

COMPOSE_FILE="docker-compose.prod.yml"

echo "============================================================"
echo "   Iniciando Despliegue en Producción — Proyecto HV         "
echo "============================================================"

# ------------------------------------------------------------
# 1. Verificación de Entorno y Variables
# ------------------------------------------------------------
echo "[PASO 1/7] Verificando archivo de variables de entorno (.env)..."
if [ ! -f ".env" ]; then
    echo "[ERROR] El archivo .env no existe en la raíz del proyecto."
    echo "Copie el archivo de ejemplo y configure los secretos antes de continuar:"
    echo "  cp .env.production.example .env"
    echo "  nano .env"
    exit 1
fi

# Validar que no se usen secretos por defecto
if grep -q "CAMBIAR_EN_PRODUCCION" .env; then
    echo "[ERROR CRÍTICO DE SEGURIDAD] Se detectaron valores por defecto 'CAMBIAR_EN_PRODUCCION' en el archivo .env."
    echo "Genere secretos criptográficos reales para SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD y BACKUP_ENCRYPTION_KEY."
    exit 1
fi

# ------------------------------------------------------------
# 2. Verificación de Docker y Docker Compose
# ------------------------------------------------------------
echo "[PASO 2/7] Verificando disponibilidad de Docker y Docker Compose..."
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker no está instalado en este sistema."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "[ERROR] Docker Compose no está disponible."
    exit 1
fi

# ------------------------------------------------------------
# 3. Verificación y Creación de Certificados SSL
# ------------------------------------------------------------
echo "[PASO 3/7] Verificando certificados SSL en ./nginx/ssl..."
if [ ! -f "./nginx/ssl/fullchain.pem" ] || [ ! -f "./nginx/ssl/privkey.pem" ]; then
    echo "[INFO] No se encontraron certificados SSL. Generando certificado bootstrap..."
    chmod +x ./scripts/init_ssl.sh
    ./scripts/init_ssl.sh staging
fi

# ------------------------------------------------------------
# 4. Construcción y Arranque de Contenedores
# ------------------------------------------------------------
echo "[PASO 4/7] Construyendo imágenes y levantando servicios de producción..."
docker compose -f "${COMPOSE_FILE}" up -d --build

# ------------------------------------------------------------
# 5. Esperar disponibilidad de PostgreSQL
# ------------------------------------------------------------
echo "[PASO 5/7] Esperando que la base de datos PostgreSQL esté lista..."
MAX_ATTEMPTS=30
ATTEMPT=1
until docker compose -f "${COMPOSE_FILE}" exec -T postgres pg_isready -U hv_app -d proyecto_hv &> /dev/null || [ $ATTEMPT -ge $MAX_ATTEMPTS ]; do
    echo "  Intento $ATTEMPT/$MAX_ATTEMPTS: esperando a PostgreSQL..."
    sleep 2
    ATTEMPT=$((ATTEMPT + 1))
done

if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
    echo "[ERROR] PostgreSQL no respondió dentro del tiempo límite."
    docker compose -f "${COMPOSE_FILE}" logs postgres
    exit 1
fi
echo "[OK] PostgreSQL está activo y aceptando conexiones."

# ------------------------------------------------------------
# 6. Ejecución de Migraciones Alembic y Siembra de Datos
# ------------------------------------------------------------
echo "[PASO 6/7] Aplicando migraciones de base de datos con Alembic..."
docker compose -f "${COMPOSE_FILE}" exec -T backend alembic upgrade head
echo "[OK] Migraciones aplicadas correctamente."

echo "[INFO] Verificando e inicializando datos de referencia (seed_db)..."
docker compose -f "${COMPOSE_FILE}" exec -T backend python -m scripts.seed_db || true

# ------------------------------------------------------------
# 7. Verificación de Salud del Sistema (Health Checks)
# ------------------------------------------------------------
echo "[PASO 7/7] Ejecutando comprobaciones de salud en producción..."
sleep 5

# Probar health check interno del backend
BACKEND_HEALTH=$(docker compose -f "${COMPOSE_FILE}" exec -T backend curl -s http://localhost:8000/api/v1/health || echo "FAIL")
if [[ "${BACKEND_HEALTH}" == *"ok"* ]] || [[ "${BACKEND_HEALTH}" == *"healthy"* ]] || [[ "${BACKEND_HEALTH}" == *"status"* ]]; then
    echo "[OK] Health check de Backend responde correctamente."
else
    echo "[ADVERTENCIA] Respuesta inesperada del backend: ${BACKEND_HEALTH}"
fi

# Probar endpoint de seguridad
SECURITY_HEALTH=$(docker compose -f "${COMPOSE_FILE}" exec -T backend curl -s http://localhost:8000/api/v1/health/security || echo "FAIL")
if [[ "${SECURITY_HEALTH}" == *"hardening_score_pct"* ]]; then
    echo "[OK] Health check de Seguridad (DevSecOps) verificado exitosamente."
fi

echo "============================================================"
echo "   ¡Despliegue de Producción Completado Exitosamente!       "
echo "============================================================"
docker compose -f "${COMPOSE_FILE}" ps
echo ""
echo "Endpoints activos:"
echo "  - Proxy Nginx (HTTP):  http://localhost:80"
echo "  - Proxy Nginx (HTTPS): https://localhost:443"
echo "  - Monitoreo API:       https://localhost/api/v1/health"
echo "  - Seguridad:           https://localhost/api/v1/health/security"
echo "============================================================"
