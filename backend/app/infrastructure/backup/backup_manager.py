"""
Data Loss Prevention (DLP) & Automated Backup Manager.

Implements requirements from Chapter 18:
- Automated database and document backup packaging
- Authenticated AES-128/HMAC symmetric encryption (Fernet)
- SHA-256 cryptographic checksums and manifest generation
- Cryptographic integrity verification (never trust completion alone)
- Restore verification drill
- Retention policy pruning
"""

import base64
import hashlib
import json
import os
import shutil
import tarfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config.settings import get_settings

logger = structlog.get_logger(__name__)
_settings = get_settings()


@dataclass
class BackupManifest:
    """Immutable manifest for an encrypted backup archive."""
    backup_id: str
    created_at: str
    backup_type: str  # "database", "documents", "full"
    file_name: str
    file_size_bytes: int
    sha256_checksum: str
    is_encrypted: bool
    record_count: int = 0
    extra_metadata: dict[str, Any] | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "BackupManifest":
        data = json.loads(json_str)
        return cls(**data)


class BackupManager:
    """
    Orchestrates backup creation, encryption, cryptographic verification,
    restoration drills, and retention management.
    """

    def __init__(self, encryption_key: str | bytes | None = None) -> None:
        self._fernet = self._init_cipher(encryption_key)

    def _init_cipher(self, key: str | bytes | None) -> Fernet:
        """Derives a deterministic 32-byte URL-safe base64 Fernet key."""
        raw_key = key or _settings.secret_key
        if isinstance(raw_key, str):
            raw_bytes = raw_key.encode("utf-8")
        else:
            raw_bytes = raw_key

        # Derive 32 bytes using PBKDF2HMAC with fixed institutional salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"proyecto_hv_institutional_dlp_salt",
            iterations=100_000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(raw_bytes))
        return Fernet(derived_key)

    @staticmethod
    def calculate_sha256(data: bytes | Path) -> str:
        """Computes SHA-256 hex digest for bytes or a file path."""
        sha256 = hashlib.sha256()
        if isinstance(data, bytes):
            sha256.update(data)
        else:
            with open(data, "rb") as f:
                while chunk := f.read(64 * 1024):
                    sha256.update(chunk)
        return sha256.hexdigest()

    def encrypt_data(self, plaintext_bytes: bytes) -> bytes:
        """Encrypts raw data using Fernet."""
        return self._fernet.encrypt(plaintext_bytes)

    def decrypt_data(self, ciphertext_bytes: bytes) -> bytes:
        """Decrypts Fernet-encrypted ciphertext."""
        return self._fernet.decrypt(ciphertext_bytes)

    def create_database_backup(
        self,
        dump_data: dict[str, Any] | list[Any],
        output_dir: Path,
        backup_id: str | None = None,
    ) -> tuple[Path, BackupManifest]:
        """
        Creates an encrypted, verified database snapshot backup.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d_%H%M%S")
        bid = backup_id or f"db_backup_{ts}"

        # 1. Serialize data
        json_bytes = json.dumps(dump_data, default=str).encode("utf-8")
        records = len(dump_data) if isinstance(dump_data, list) else len(dump_data.keys())

        # 2. Encrypt
        encrypted_bytes = self.encrypt_data(json_bytes)
        checksum = self.calculate_sha256(encrypted_bytes)

        # 3. Write archive and manifest
        archive_name = f"{bid}.enc"
        archive_path = output_dir / archive_name
        archive_path.write_bytes(encrypted_bytes)

        manifest = BackupManifest(
            backup_id=bid,
            created_at=now.isoformat(),
            backup_type="database",
            file_name=archive_name,
            file_size_bytes=len(encrypted_bytes),
            sha256_checksum=checksum,
            is_encrypted=True,
            record_count=records,
            extra_metadata={"format": "json_encrypted"},
        )

        manifest_path = output_dir / f"{bid}.manifest.json"
        manifest_path.write_text(manifest.to_json(), encoding="utf-8")

        logger.info("database_backup_created", backup_id=bid, size=len(encrypted_bytes))
        return archive_path, manifest

    def create_documents_backup(
        self,
        documents_dir: Path,
        output_dir: Path,
        backup_id: str | None = None,
    ) -> tuple[Path, BackupManifest]:
        """
        Packages and encrypts the document storage directory.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d_%H%M%S")
        bid = backup_id or f"docs_backup_{ts}"

        tar_temp_path = output_dir / f"{bid}_temp.tar.gz"

        # Count documents
        doc_count = 0
        with tarfile.open(tar_temp_path, "w:gz") as tar:
            if documents_dir.exists():
                for item in documents_dir.rglob("*"):
                    if item.is_file():
                        arcname = item.relative_to(documents_dir)
                        tar.add(item, arcname=str(arcname))
                        doc_count += 1

        try:
            tar_bytes = tar_temp_path.read_bytes()
        finally:
            if tar_temp_path.exists():
                tar_temp_path.unlink()

        # Encrypt archive
        encrypted_bytes = self.encrypt_data(tar_bytes)
        checksum = self.calculate_sha256(encrypted_bytes)

        archive_name = f"{bid}.enc"
        archive_path = output_dir / archive_name
        archive_path.write_bytes(encrypted_bytes)

        manifest = BackupManifest(
            backup_id=bid,
            created_at=now.isoformat(),
            backup_type="documents",
            file_name=archive_name,
            file_size_bytes=len(encrypted_bytes),
            sha256_checksum=checksum,
            is_encrypted=True,
            record_count=doc_count,
            extra_metadata={"source_dir": str(documents_dir)},
        )

        manifest_path = output_dir / f"{bid}.manifest.json"
        manifest_path.write_text(manifest.to_json(), encoding="utf-8")

        logger.info("documents_backup_created", backup_id=bid, files=doc_count, size=len(encrypted_bytes))
        return archive_path, manifest

    def verify_backup_integrity(self, archive_path: Path, manifest: BackupManifest) -> bool:
        """
        Cryptographically verifies a backup file against its manifest.
        Validates existence, file size, SHA-256 checksum, and decryption viability.
        """
        if not archive_path.exists():
            logger.error("backup_verification_failed_missing_file", path=str(archive_path))
            return False

        actual_size = archive_path.stat().st_size
        if actual_size != manifest.file_size_bytes:
            logger.error("backup_verification_size_mismatch", expected=manifest.file_size_bytes, actual=actual_size)
            return False

        actual_checksum = self.calculate_sha256(archive_path)
        if actual_checksum != manifest.sha256_checksum:
            logger.error("backup_verification_checksum_mismatch", expected=manifest.sha256_checksum, actual=actual_checksum)
            return False

        # Verify decryption works without errors
        try:
            raw_bytes = archive_path.read_bytes()
            self.decrypt_data(raw_bytes)
        except Exception as exc:
            logger.error("backup_verification_decryption_failed", error=str(exc))
            return False

        logger.info("backup_integrity_verified_ok", backup_id=manifest.backup_id)
        return True

    def test_restore_drill(self, archive_path: Path, manifest: BackupManifest, drill_dir: Path) -> bool:
        """
        Executes a restore drill test to verify that the backup can be successfully recovered.
        """
        if not self.verify_backup_integrity(archive_path, manifest):
            return False

        drill_dir.mkdir(parents=True, exist_ok=True)
        try:
            encrypted_data = archive_path.read_bytes()
            decrypted_bytes = self.decrypt_data(encrypted_data)

            if manifest.backup_type == "database":
                # Parse json
                parsed = json.loads(decrypted_bytes.decode("utf-8"))
                test_file = drill_dir / f"{manifest.backup_id}_restored.json"
                test_file.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
                return test_file.exists() and test_file.stat().st_size > 0

            elif manifest.backup_type == "documents":
                # Extract tar.gz
                tar_temp = drill_dir / "temp_restore.tar.gz"
                tar_temp.write_bytes(decrypted_bytes)
                try:
                    with tarfile.open(tar_temp, "r:gz") as tar:
                        tar.extractall(drill_dir)
                    return True
                finally:
                    if tar_temp.exists():
                        tar_temp.unlink()

            return False
        except Exception as exc:
            logger.error("restore_drill_failed", error=str(exc))
            return False

    def prune_backups(self, backup_dir: Path, retention_days: int = 7) -> list[Path]:
        """
        Prunes backups older than the retention threshold.
        Deletes both the .enc archive and the companion .manifest.json.
        """
        if not backup_dir.exists():
            return []

        cutoff = time.time() - (retention_days * 86400)
        pruned_files: list[Path] = []

        for item in backup_dir.glob("*.enc"):
            if item.is_file() and item.stat().st_mtime < cutoff:
                companion_manifest = backup_dir / f"{item.stem}.manifest.json"
                try:
                    item.unlink()
                    pruned_files.append(item)
                    if companion_manifest.exists():
                        companion_manifest.unlink()
                        pruned_files.append(companion_manifest)
                    logger.info("backup_pruned", file=str(item))
                except Exception as exc:
                    logger.error("backup_prune_error", file=str(item), error=str(exc))

        return pruned_files
