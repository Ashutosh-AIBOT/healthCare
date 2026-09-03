"""MinIO / local filesystem object storage helper (M4 walking skeleton)."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

_LOCAL_ROOT = Path("/tmp/aarogya-storage")
_minio_client = None
_use_local = False


def _init_client() -> None:
    global _minio_client, _use_local
    if _minio_client is not None or _use_local:
        return
    try:
        from minio import Minio

        _minio_client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        # Probe connectivity lightly; fall back on failure
        _minio_client.list_buckets()
    except Exception:
        logger.warning("MinIO unavailable; using local storage at %s", _LOCAL_ROOT)
        _minio_client = None
        _use_local = True
        _LOCAL_ROOT.mkdir(parents=True, exist_ok=True)


def ensure_bucket(bucket: str | None = None) -> str:
    """Ensure the reports bucket exists (MinIO) or local dir is ready."""
    bucket = bucket or settings.minio_bucket_reports
    _init_client()
    if _use_local or _minio_client is None:
        (_LOCAL_ROOT / bucket).mkdir(parents=True, exist_ok=True)
        return bucket
    from minio.error import S3Error

    try:
        if not _minio_client.bucket_exists(bucket):
            _minio_client.make_bucket(bucket)
    except S3Error:
        logger.warning("ensure_bucket failed for %s; continuing", bucket)
    return bucket


def put_object(
    object_key: str,
    data: bytes,
    *,
    content_type: str = "application/pdf",
    bucket: str | None = None,
) -> str:
    """Store bytes under object_key. Returns the object key."""
    bucket = ensure_bucket(bucket)
    _init_client()
    if _use_local or _minio_client is None:
        path = _LOCAL_ROOT / bucket / object_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return object_key

    from io import BytesIO

    _minio_client.put_object(
        bucket,
        object_key,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return object_key


def presign_put(
    object_key: str,
    *,
    expires_seconds: int = 900,
    content_type: str = "application/pdf",
    bucket: str | None = None,
) -> str:
    """Return a presigned PUT URL (or a local file:// style path for fallback)."""
    bucket = ensure_bucket(bucket)
    _init_client()
    if _use_local or _minio_client is None:
        # Client uploads via API confirm path; return a local hint URL
        path = _LOCAL_ROOT / bucket / object_key
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"file://{path}"

    from datetime import timedelta

    return _minio_client.presigned_put_object(
        bucket,
        object_key,
        expires=timedelta(seconds=expires_seconds),
    )


def get_object_bytes(object_key: str, *, bucket: str | None = None) -> bytes:
    """Fetch object bytes from MinIO or local fallback."""
    bucket = bucket or settings.minio_bucket_reports
    _init_client()
    if _use_local or _minio_client is None:
        path = _LOCAL_ROOT / bucket / object_key
        if not path.is_file():
            return b""
        return path.read_bytes()

    response = _minio_client.get_object(bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def make_object_key(family_id: uuid.UUID, filename: str) -> str:
    """Build a non-PHI object key (ids + sanitized extension only)."""
    safe_name = Path(filename).name.replace(" ", "_")
    # Keep extension only in logs elsewhere; key uses uuid + short suffix
    ext = Path(safe_name).suffix.lower() or ".pdf"
    if len(ext) > 8:
        ext = ".bin"
    return f"{family_id}/{uuid.uuid4()}{ext}"


def local_upload_path(object_key: str, *, bucket: str | None = None) -> Path:
    bucket = bucket or settings.minio_bucket_reports
    return _LOCAL_ROOT / bucket / object_key
