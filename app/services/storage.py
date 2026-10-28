from pathlib import Path
from typing import Protocol

from app.core.config import Settings, get_settings


class StorageBackend(Protocol):
    def save(self, key: str, data: bytes, content_type: str) -> None: ...
    def delete(self, key: str) -> None: ...
    def local_path(self, key: str) -> Path | None: ...
    def presigned_url(self, key: str) -> str | None: ...


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Invalid storage key")
        return path

    def save(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def local_path(self, key: str) -> Path | None:
        path = self._path(key)
        return path if path.is_file() else None

    def presigned_url(self, key: str) -> str | None:
        return None


class S3Storage:
    def __init__(self, settings: Settings) -> None:
        import boto3  # imported lazily so local development does not need AWS config

        self.bucket = settings.s3_bucket
        self.expiry = settings.s3_presign_expiry_seconds
        self.client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=(
                settings.s3_secret_access_key.get_secret_value() if settings.s3_secret_access_key else None
            ),
        )

    def save(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, CacheControl="max-age=86400"
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def local_path(self, key: str) -> Path | None:
        return None

    def presigned_url(self, key: str) -> str | None:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=self.expiry
        )


_storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _storage
    if _storage is None:
        settings = get_settings()
        _storage = (
            S3Storage(settings) if settings.storage_backend == "s3" else LocalStorage(settings.local_storage_path)
        )
    return _storage
