"""
Unit tests for the BackupManager & Data Loss Prevention (DLP) engine.
"""

import json
import time
from pathlib import Path

from app.infrastructure.backup.backup_manager import BackupManager, BackupManifest


def test_encryption_decryption_roundtrip():
    manager = BackupManager()
    plaintext = b"Informacion institucional altamente confidencial de hojas de vida"
    encrypted = manager.encrypt_data(plaintext)
    assert encrypted != plaintext

    decrypted = manager.decrypt_data(encrypted)
    assert decrypted == plaintext


def test_calculate_sha256_bytes_and_file(tmp_path: Path):
    manager = BackupManager()
    data = b"Prueba de hash SHA-256 para integridad de copias de seguridad."
    hash_from_bytes = manager.calculate_sha256(data)
    assert len(hash_from_bytes) == 64

    test_file = tmp_path / "test_hash.dat"
    test_file.write_bytes(data)
    hash_from_file = manager.calculate_sha256(test_file)
    assert hash_from_bytes == hash_from_file


def test_create_database_backup_and_manifest(tmp_path: Path):
    manager = BackupManager()
    sample_db = {
        "persons": [{"id": 1, "name": "Carolina Marin"}],
        "documents": [{"id": "doc-1", "file": "cv.pdf"}],
    }

    archive_path, manifest = manager.create_database_backup(sample_db, tmp_path)

    assert archive_path.exists()
    assert archive_path.stat().st_size > 0
    assert manifest.backup_type == "database"
    assert manifest.is_encrypted is True
    assert manifest.sha256_checksum == manager.calculate_sha256(archive_path)

    manifest_file = tmp_path / f"{manifest.backup_id}.manifest.json"
    assert manifest_file.exists()


def test_create_documents_backup(tmp_path: Path):
    manager = BackupManager()
    docs_source = tmp_path / "source_docs"
    docs_source.mkdir()
    (docs_source / "doc1.pdf").write_bytes(b"%PDF-sample-1")
    (docs_source / "doc2.pdf").write_bytes(b"%PDF-sample-2")

    backup_dir = tmp_path / "backups"
    archive_path, manifest = manager.create_documents_backup(docs_source, backup_dir)

    assert archive_path.exists()
    assert manifest.backup_type == "documents"
    assert manifest.record_count == 2
    assert manager.verify_backup_integrity(archive_path, manifest) is True


def test_verify_backup_integrity_detects_tampering(tmp_path: Path):
    manager = BackupManager()
    sample_data = {"test": 123}
    archive_path, manifest = manager.create_database_backup(sample_data, tmp_path)

    # Untampered passes
    assert manager.verify_backup_integrity(archive_path, manifest) is True

    # Tamper with file content
    tampered_bytes = archive_path.read_bytes() + b"\x00corrupted"
    archive_path.write_bytes(tampered_bytes)

    # Now verification must fail
    assert manager.verify_backup_integrity(archive_path, manifest) is False


def test_restore_drill_success(tmp_path: Path):
    manager = BackupManager()
    original_data = {"empresa": "Proyecto HV", "version": 1}
    archive_path, manifest = manager.create_database_backup(original_data, tmp_path / "out")

    drill_dir = tmp_path / "drill"
    success = manager.test_restore_drill(archive_path, manifest, drill_dir)
    assert success is True

    restored_file = drill_dir / f"{manifest.backup_id}_restored.json"
    assert restored_file.exists()
    restored_data = json.loads(restored_file.read_text(encoding="utf-8"))
    assert restored_data == original_data


def test_prune_backups(tmp_path: Path):
    manager = BackupManager()
    backup_dir = tmp_path / "retention_test"
    backup_dir.mkdir()

    archive_path, manifest = manager.create_database_backup({"item": 1}, backup_dir)
    manifest_path = backup_dir / f"{manifest.backup_id}.manifest.json"

    # Mock file mtime to 10 days ago
    old_time = time.time() - (10 * 86400)
    import os
    os.utime(archive_path, (old_time, old_time))
    os.utime(manifest_path, (old_time, old_time))

    # Prune with 7 days retention
    pruned = manager.prune_backups(backup_dir, retention_days=7)
    assert len(pruned) == 2
    assert not archive_path.exists()
    assert not manifest_path.exists()
