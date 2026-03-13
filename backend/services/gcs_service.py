from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GcsServiceConfig:
    bucket_name: str | None = None
    prefix: str = "pitch-decks"


class GcsService:
    def __init__(self, config: GcsServiceConfig | None = None) -> None:
        self._config = config or GcsServiceConfig()

    def upload_file(self, local_path: Path) -> dict[str, str | None]:
        if not self._config.bucket_name:
            logger.warning("GCS_BUCKET_NAME is not configured. Skipping upload.")
            return {"bucket": None, "object": None, "url": None}

        from google.cloud import storage
        import datetime
        try:
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            client = storage.Client(project=project) if project else storage.Client()
            bucket = client.bucket(self._config.bucket_name)
            blob_name = f"{self._config.prefix}/{local_path.name}"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(str(local_path))
            
            # Use signed URL since public access is restricted
            url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(hours=1),
                method="GET"
            )
            logger.info(f"Uploaded {local_path} and generated signed URL")
            return {"bucket": self._config.bucket_name, "object": blob_name, "url": url}
        except Exception as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            return {"bucket": self._config.bucket_name, "object": None, "url": None}


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def _get_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _ensure_bucket_public_read(bucket) -> None:
    policy = bucket.get_iam_policy(requested_policy_version=3)
    bindings = list(policy.bindings or [])
    for b in bindings:
        if b.get("role") == "roles/storage.objectViewer" and "allUsers" in set(b.get("members") or []):
            return
    bindings.append({"role": "roles/storage.objectViewer", "members": {"allUsers"}})
    policy.bindings = bindings
    bucket.set_iam_policy(policy)


def upload_file(local_path: str, destination_blob_name: str) -> str:
    from google.cloud import storage
    import datetime

    bucket_name = _require_env("GCS_BUCKET_NAME")
    project = _get_env("GOOGLE_CLOUD_PROJECT")

    try:
        client = storage.Client(project=project) if project else storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_path)
        
        # Use signed URL since Public Access Prevention is enforced on many buckets
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET"
        )
        logger.info(f"Uploaded {local_path} and generated signed URL")
        return url
    except Exception as e:
        logger.error(f"Failed to upload {local_path} to GCS: {e}")
        raise


def upload_bytes(data: bytes, destination_blob_name: str, content_type: str) -> str:
    from google.cloud import storage
    import datetime

    bucket_name = _require_env("GCS_BUCKET_NAME")
    project = _get_env("GOOGLE_CLOUD_PROJECT")

    try:
        client = storage.Client(project=project) if project else storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_string(data, content_type=content_type)
        
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET"
        )
        logger.info(f"Uploaded bytes and generated signed URL")
        return url
    except Exception as e:
        logger.error(f"Failed to upload bytes to GCS: {e}")
        raise


def ensure_bucket_exists() -> None:
    from google.cloud import storage
    from google.cloud import exceptions as gcloud_exceptions
    from google.api_core import exceptions as gax_exceptions

    bucket_name = _require_env("GCS_BUCKET_NAME")
    project = _get_env("GOOGLE_CLOUD_PROJECT")
    location = _get_env("GOOGLE_CLOUD_LOCATION")

    try:
        client = storage.Client(project=project) if project else storage.Client()
        bucket = client.lookup_bucket(bucket_name)
        if bucket is None:
            bucket = storage.Bucket(client, name=bucket_name)
            if location:
                bucket.location = location
            bucket.iam_configuration.uniform_bucket_level_access_enabled = True
            try:
                if location:
                    client.create_bucket(bucket, location=location)
                else:
                    client.create_bucket(bucket)
                logger.info(f"Created bucket {bucket_name}")
            except (gcloud_exceptions.Conflict, gax_exceptions.Conflict):
                logger.info(f"Bucket {bucket_name} already exists (concurrently created)")
            except Exception as e:
                logger.error(f"Failed to create bucket {bucket_name}: {e}")
                return

        if bucket and not bucket.iam_configuration.uniform_bucket_level_access_enabled:
            try:
                bucket.iam_configuration.uniform_bucket_level_access_enabled = True
                bucket.patch()
                logger.info(f"Enabled uniform bucket level access for {bucket_name}")
            except Exception as e:
                logger.warning(f"Could not update uniform bucket level access for {bucket_name}: {e}")
    except Exception as e:
        logger.error(f"GCS ensure_bucket_exists failed: {e}")
