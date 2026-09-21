#!/usr/bin/env bash
# ============================================================
# Proyecto HV — Script Automatizado de Respaldo Cifrado (Cron)
# ============================================================
# Uso en crontab (ej. diario a las 02:00 AM):
#   0 2 * * * cd /ruta/al/proyecto && ./scripts/backup_cron.sh >> /var/log/hv_backup.log 2>&1
# ============================================================

set -e

COMPOSE_FILE="docker-compose.prod.yml"
DATE_TAG=$(date +"%Y%m%d_%H%M%S")

echo "============================================================"
echo " [${DATE_TAG}] Iniciando Respaldo Cifrado Institucional"
echo "============================================================"

# Verificar que los contenedores estén activos
if ! docker compose -f "${COMPOSE_FILE}" ps | grep -q "hv_backend_prod"; then
    echo "[ERROR] El contenedor backend de producción no está en ejecución."
    exit 1
fi

# Ejecutar el respaldo dentro del contenedor backend invocando BackupManager
echo "[INFO] Generando copias de seguridad de Base de Datos y Repositorio de Documentos..."
docker compose -f "${COMPOSE_FILE}" exec -T backend python -c "
import asyncio
from app.infrastructure.backup.backup_manager import BackupManager
from app.config.settings import get_settings

async def run_backup():
    settings = get_settings()
    manager = BackupManager()
    
    print('1. Creando snapshot cifrado de PostgreSQL...')
    db_manifest = await manager.create_database_backup()
    print(f'   [OK] DB Backup generado: {db_manifest.filename} (Hash: {db_manifest.sha256_checksum[:16]}...)')
    
    print('2. Creando snapshot cifrado del repositorio de documentos...')
    doc_manifest = await manager.create_documents_backup()
    print(f'   [OK] Docs Backup generado: {doc_manifest.filename} (Hash: {doc_manifest.sha256_checksum[:16]}...)')
    
    print('3. Verificando integridad criptográfica de los respaldos generados...')
    assert manager.verify_backup_integrity(db_manifest.filename), 'Fallo de verificación de integridad en BD'
    assert manager.verify_backup_integrity(doc_manifest.filename), 'Fallo de verificación de integridad en Documentos'
    print('   [OK] Integridad SHA-256 y descifrado verificados al 100%.')
    
    print('4. Purgando respaldos antiguos según política de retención...')
    pruned = manager.prune_backups(max_age_days=settings.BACKUP_RETENTION_DAYS_LOCAL)
    print(f'   [OK] {len(pruned)} respaldos obsoletos purgados exitosamente.')

asyncio.run(run_backup())
"

echo "[OK] Respaldo finalizado con éxito a las $(date +"%Y-%m-%d %H:%M:%S")."
