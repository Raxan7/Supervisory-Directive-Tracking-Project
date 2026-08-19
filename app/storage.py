from functools import lru_cache
from io import BytesIO
from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings


@lru_cache
def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(settings.minio_endpoint, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, secure=settings.minio_secure)


def ensure_bucket() -> None:
    settings = get_settings()
    client = get_minio_client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def upload_file(object_key: str, content: bytes, content_type: str) -> None:
    settings = get_settings()
    client = get_minio_client()
    client.put_object(settings.minio_bucket, object_key, BytesIO(content), length=len(content), content_type=content_type)


def download_file(object_key: str) -> bytes | None:
    settings = get_settings()
    client = get_minio_client()
    try:
        response = client.get_object(settings.minio_bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except S3Error:
        return None


def delete_file(object_key: str) -> None:
    settings = get_settings()
    client = get_minio_client()
    client.remove_object(settings.minio_bucket, object_key)