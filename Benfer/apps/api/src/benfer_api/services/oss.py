from datetime import datetime
from pathlib import Path
import secrets
from typing import BinaryIO, Optional

import oss2

from benfer_api.core.config import get_settings
from benfer_api.schemas.file import FilePartETag

settings = get_settings()


class OSSService:
    def __init__(self):
        self.auth = oss2.Auth(
            settings.ALIYUN_OSS_ACCESS_KEY_ID,
            settings.ALIYUN_OSS_ACCESS_KEY_SECRET,
        )
        self.bucket = oss2.Bucket(
            self.auth,
            settings.ALIYUN_OSS_ENDPOINT,
            settings.ALIYUN_OSS_BUCKET,
            connect_timeout=10,
        )

    def generate_oss_key(self, filename: str, user_id: Optional[str] = None) -> str:
        """Generate OSS object key with stable prefix and random suffix."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        prefix = f"{settings.ALIYUN_OSS_PREFIX}/{timestamp}"
        if user_id:
            prefix = f"{prefix}/{user_id}"

        safe_filename = Path(filename).name.replace(" ", "_")
        random_suffix = secrets.token_hex(4)
        return f"{prefix}/{random_suffix}_{safe_filename}"

    def get_upload_url(self, oss_key: str, expires_in: Optional[int] = None) -> str:
        """Generate presigned upload URL for single-part upload."""
        ttl = expires_in or settings.PRESIGNED_URL_EXPIRES_SECONDS
        return self.bucket.sign_url("PUT", oss_key, ttl)

    def get_download_url(self, oss_key: str, expires_in: Optional[int] = None) -> str:
        """Generate presigned download URL."""
        ttl = expires_in or settings.PRESIGNED_URL_EXPIRES_SECONDS
        return self.bucket.sign_url("GET", oss_key, ttl)

    def init_multipart_upload(self, oss_key: str, content_type: Optional[str] = None) -> str:
        """Initialize multipart upload and return upload ID."""
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        result = self.bucket.init_multipart_upload(oss_key, headers=headers)
        return result.upload_id

    def get_multipart_upload_url(
        self,
        oss_key: str,
        multipart_upload_id: str,
        part_number: int,
        expires_in: Optional[int] = None,
    ) -> str:
        """Generate presigned URL for a multipart upload chunk."""
        ttl = expires_in or settings.PRESIGNED_URL_EXPIRES_SECONDS
        params = {
            "uploadId": multipart_upload_id,
            "partNumber": str(part_number),
        }
        return self.bucket.sign_url("PUT", oss_key, ttl, params=params)

    def complete_multipart_upload(
        self,
        oss_key: str,
        multipart_upload_id: str,
        parts: list[FilePartETag],
    ) -> None:
        """Complete multipart upload with part number/etag pairs."""
        if not parts:
            raise ValueError("parts must not be empty")

        part_infos = [
            oss2.models.PartInfo(item.part_number, item.etag.strip('"'))
            for item in sorted(parts, key=lambda x: x.part_number)
        ]
        self.bucket.complete_multipart_upload(oss_key, multipart_upload_id, part_infos)

    def upload_file(
        self,
        oss_key: str,
        file_content: bytes | BinaryIO,
        content_type: Optional[str] = None,
    ) -> bool:
        """Upload file to OSS."""
        try:
            headers = {}
            if content_type:
                headers["Content-Type"] = content_type
            self.bucket.put_object(oss_key, file_content, headers=headers)
            return True
        except Exception as exc:
            print(f"OSS upload error: {exc}")
            return False

    def delete_file(self, oss_key: str) -> bool:
        """Delete file from OSS."""
        try:
            self.bucket.delete_object(oss_key)
            return True
        except Exception as exc:
            print(f"OSS delete error: {exc}")
            return False

    def file_exists(self, oss_key: str) -> bool:
        """Check if file exists in OSS."""
        try:
            return self.bucket.object_exists(oss_key)
        except Exception:
            return False


def get_oss_service() -> OSSService:
    return OSSService()
