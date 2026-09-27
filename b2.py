import hashlib
import logging
import mimetypes
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import requests

from settings import (
    B2_APPLICATION_KEY,
    B2_APPLICATION_KEY_ID,
    B2_API_URL,
)

logger = logging.getLogger(__name__)

B2_API_VERSION = "v4"
DEFAULT_API_URL = "https://api.backblazeb2.com"
# b2_upload_file supports files up to 5 GiB; anything larger must use the
# large-file (multipart) flow.
MAX_SINGLE_UPLOAD_SIZE = 5 * 1024 * 1024 * 1024
LARGE_FILE_PART_SIZE = 100 * 1024 * 1024

API_TIMEOUT = 30
UPLOAD_TIMEOUT = 3600


class B2Error(Exception):
    pass


class B2Client:
    """Minimal Backblaze B2 native API (v4) client for uploads."""

    def __init__(self, application_key_id, application_key, api_url=None):
        self._application_key_id = application_key_id
        self._application_key = application_key
        self._api_url = (api_url or DEFAULT_API_URL).rstrip("/")
        self._auth = None

    def _authorize(self):
        if self._auth is not None:
            return self._auth
        resp = requests.get(
            f"{self._api_url}/b2api/{B2_API_VERSION}/b2_authorize_account",
            auth=(self._application_key_id, self._application_key),
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        storage = data["apiInfo"]["storageApi"]
        self._auth = {
            "authorizationToken": data["authorizationToken"],
            "apiUrl": storage["apiUrl"],
            "downloadUrl": storage["downloadUrl"],
            "buckets": {
                bucket["name"]: bucket["id"]
                for bucket in storage.get("allowed", {}).get("buckets", [])
                if bucket.get("name")
            },
        }
        return self._auth

    def _bucket_id(self, bucket_name):
        auth = self._authorize()
        bucket_id = auth["buckets"].get(bucket_name)
        if not bucket_id:
            raise B2Error(
                f"Bucket {bucket_name!r} is not accessible with this application key"
            )
        return bucket_id

    def upload_file(self, local_path, bucket, key, extra_args=None):
        auth = self._authorize()
        bucket_id = self._bucket_id(bucket)
        size = Path(local_path).stat().st_size
        if size > MAX_SINGLE_UPLOAD_SIZE:
            self._upload_large_file(local_path, bucket_id, key, auth)
        else:
            self._upload_single_file(local_path, bucket_id, key, auth)
        logger.info("Uploaded %s to b2://%s/%s", local_path, bucket, key)

    def _upload_single_file(self, local_path, bucket_id, key, auth):
        upload = self._get_upload_url(bucket_id, auth)
        headers = {
            "Authorization": upload["authorizationToken"],
            "X-Bz-File-Name": quote(key, safe="/"),
            "Content-Type": self._content_type(local_path),
            "Content-Length": str(Path(local_path).stat().st_size),
            "X-Bz-Content-Sha1": self._file_sha1(local_path),
        }
        with open(local_path, "rb") as f:
            resp = requests.post(
                upload["uploadUrl"], data=f, headers=headers, timeout=UPLOAD_TIMEOUT
            )
        resp.raise_for_status()

    def _upload_large_file(self, local_path, bucket_id, key, auth):
        resp = requests.post(
            f"{auth['apiUrl']}/b2api/{B2_API_VERSION}/b2_start_large_file",
            json={
                "bucketId": bucket_id,
                "fileName": key,
                "contentType": self._content_type(local_path),
            },
            headers={"Authorization": auth["authorizationToken"]},
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        file_id = resp.json()["fileId"]

        resp = requests.get(
            f"{auth['apiUrl']}/b2api/{B2_API_VERSION}/b2_get_upload_part_url",
            params={"fileId": file_id},
            headers={"Authorization": auth["authorizationToken"]},
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        part_upload = resp.json()

        part_sha1s = []
        part_number = 1
        with open(local_path, "rb") as f:
            while True:
                part = f.read(LARGE_FILE_PART_SIZE)
                if not part:
                    break
                sha1 = hashlib.sha1(part, usedforsecurity=False).hexdigest()
                headers = {
                    "Authorization": part_upload["authorizationToken"],
                    "X-Bz-Part-Number": str(part_number),
                    "Content-Length": str(len(part)),
                    "X-Bz-Content-Sha1": sha1,
                }
                resp = requests.post(
                    part_upload["uploadUrl"],
                    data=part,
                    headers=headers,
                    timeout=UPLOAD_TIMEOUT,
                )
                resp.raise_for_status()
                part_sha1s.append(sha1)
                part_number += 1

        resp = requests.post(
            f"{auth['apiUrl']}/b2api/{B2_API_VERSION}/b2_finish_large_file",
            json={"fileId": file_id, "partSha1Array": part_sha1s},
            headers={"Authorization": auth["authorizationToken"]},
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()

    def _get_upload_url(self, bucket_id, auth):
        resp = requests.get(
            f"{auth['apiUrl']}/b2api/{B2_API_VERSION}/b2_get_upload_url",
            params={"bucketId": bucket_id},
            headers={"Authorization": auth["authorizationToken"]},
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _content_type(local_path):
        return mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"

    @staticmethod
    def _file_sha1(local_path):
        sha1 = hashlib.sha1(usedforsecurity=False)
        with open(local_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                sha1.update(chunk)
        return sha1.hexdigest()


@lru_cache(maxsize=1)
def get_b2_client():
    if bool(B2_APPLICATION_KEY_ID) != bool(B2_APPLICATION_KEY):
        raise ValueError(
            "B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY must be set together"
        )
    return B2Client(
        application_key_id=B2_APPLICATION_KEY_ID,
        application_key=B2_APPLICATION_KEY,
        api_url=B2_API_URL,
    )
