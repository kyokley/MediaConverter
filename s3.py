import logging
import mimetypes
from functools import lru_cache

import boto3
from botocore.config import Config

from settings import (
    S3_ACCESS_KEY_ID,
    S3_ENDPOINT_URL,
    S3_REGION_NAME,
    S3_SECRET_ACCESS_KEY,
)

logger = logging.getLogger(__name__)


class S3Client:
    """Thin wrapper around boto3 for S3-compatible storage backends."""

    def __init__(self, endpoint_url, access_key_id, secret_access_key, region_name):
        kwargs = {
            "region_name": region_name,
            "config": Config(signature_version="s3v4"),
        }
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        if access_key_id:
            kwargs["aws_access_key_id"] = access_key_id
        if secret_access_key:
            kwargs["aws_secret_access_key"] = secret_access_key
        self._client = boto3.client("s3", **kwargs)

    def upload_file(self, local_path, bucket, key, extra_args=None):
        extra_args = dict(extra_args or {})
        extra_args.setdefault(
            "ContentType",
            mimetypes.guess_type(str(local_path))[0] or "application/octet-stream",
        )
        self._client.upload_file(str(local_path), bucket, key, ExtraArgs=extra_args)
        logger.info("Uploaded %s to s3://%s/%s", local_path, bucket, key)


@lru_cache(maxsize=1)
def get_s3_client():
    if bool(S3_ACCESS_KEY_ID) != bool(S3_SECRET_ACCESS_KEY):
        raise ValueError(
            "S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY must be set together"
        )
    return S3Client(
        endpoint_url=S3_ENDPOINT_URL,
        access_key_id=S3_ACCESS_KEY_ID,
        secret_access_key=S3_SECRET_ACCESS_KEY,
        region_name=S3_REGION_NAME,
    )
