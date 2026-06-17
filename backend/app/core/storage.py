from __future__ import annotations

from functools import lru_cache
from datetime import timedelta
from urllib.parse import urlparse

from minio import Minio

from app.core.config import settings


@lru_cache(maxsize=1)
def get_object_storage_client() -> Minio:
    parsed = urlparse(settings.object_storage_endpoint)
    endpoint = settings.object_storage_endpoint
    secure = settings.object_storage_secure

    if parsed.scheme:
        endpoint = parsed.netloc or parsed.path
        secure = parsed.scheme == "https"

    kwargs = {
        "access_key": settings.object_storage_access_key,
        "secret_key": settings.object_storage_secret_key,
        "secure": secure,
    }
    if settings.object_storage_region:
        kwargs["region"] = settings.object_storage_region

    return Minio(endpoint, **kwargs)


def ensure_media_bucket() -> None:
    client = get_object_storage_client()
    if not client.bucket_exists(settings.object_storage_bucket):
        client.make_bucket(settings.object_storage_bucket)


def presigned_media_url(bucket: str, key: str) -> str:
    client = get_object_storage_client()
    return client.presigned_get_object(
        bucket,
        key,
        expires=timedelta(minutes=settings.object_storage_signed_url_expiry_minutes),
    )
