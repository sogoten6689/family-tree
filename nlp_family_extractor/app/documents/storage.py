from __future__ import annotations

import os
from typing import BinaryIO, Optional

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


class ObjectStorageError(Exception):
    pass


class ObjectStorageConfig:
    def __init__(self) -> None:
        self.endpoint = os.getenv("MINIO_ENDPOINT") or os.getenv("S3_ENDPOINT")
        self.public_endpoint = os.getenv("MINIO_PUBLIC_ENDPOINT") or self.endpoint
        self.access_key = os.getenv("MINIO_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("MINIO_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.bucket = os.getenv("MINIO_BUCKET") or os.getenv("S3_BUCKET")
        self.region = os.getenv("MINIO_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        self.use_ssl = (os.getenv("MINIO_USE_SSL", "false").lower() == "true")
        self.auto_create_bucket = os.getenv("MINIO_AUTO_CREATE_BUCKET", "true").lower() == "true"
        self.presign_expires = int(os.getenv("MINIO_PRESIGN_EXPIRES", "3600"))

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint and self.access_key and self.secret_key and self.bucket)


class ObjectStorage:
    def __init__(self, config: Optional[ObjectStorageConfig] = None) -> None:
        self.config = config or ObjectStorageConfig()
        self._internal_client: Optional[BaseClient] = None
        self._public_client: Optional[BaseClient] = None

    @classmethod
    def from_env(cls) -> "ObjectStorage":
        return cls(ObjectStorageConfig())

    def _build_client(self, endpoint: Optional[str]) -> BaseClient:
        if not endpoint:
            raise ObjectStorageError("Object storage endpoint is not configured.")

        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            region_name=self.config.region,
            use_ssl=self.config.use_ssl,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    @property
    def internal_client(self) -> BaseClient:
        if self._internal_client is None:
            self._internal_client = self._build_client(self.config.endpoint)
        return self._internal_client

    @property
    def public_client(self) -> BaseClient:
        if self._public_client is None:
            self._public_client = self._build_client(self.config.public_endpoint)
        return self._public_client

    def ensure_bucket(self) -> None:
        if not self.config.enabled:
            raise ObjectStorageError("Object storage is not configured.")

        if not self.config.auto_create_bucket:
            return

        try:
            self.internal_client.head_bucket(Bucket=self.config.bucket)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code not in {"404", "NoSuchBucket", "403", "NotFound"}:
                raise ObjectStorageError(f"Cannot access bucket: {exc}") from exc
            try:
                self.internal_client.create_bucket(Bucket=self.config.bucket)
            except (ClientError, BotoCoreError) as create_exc:
                raise ObjectStorageError(f"Cannot create bucket: {create_exc}") from create_exc

    def upload_file(
        self,
        file_key: str,
        file_obj: BinaryIO,
        *,
        content_type: str,
        size: Optional[int] = None,
    ) -> None:
        if not self.config.enabled:
            raise ObjectStorageError("Object storage is not configured.")

        extra_args = {"ContentType": content_type}
        try:
            if size is not None:
                self.internal_client.upload_fileobj(
                    file_obj,
                    self.config.bucket,
                    file_key,
                    ExtraArgs=extra_args,
                )
            else:
                self.internal_client.upload_fileobj(
                    file_obj,
                    self.config.bucket,
                    file_key,
                    ExtraArgs=extra_args,
                )
        except (ClientError, BotoCoreError) as exc:
            raise ObjectStorageError(f"Upload failed: {exc}") from exc

    def get_presigned_url(self, file_key: str, expires_in: Optional[int] = None) -> str:
        if not self.config.enabled:
            raise ObjectStorageError("Object storage is not configured.")

        try:
            return self.public_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.config.bucket, "Key": file_key},
                ExpiresIn=expires_in or self.config.presign_expires,
            )
        except (ClientError, BotoCoreError) as exc:
            raise ObjectStorageError(f"Cannot generate presigned URL: {exc}") from exc

    def delete_file(self, file_key: str) -> None:
        if not self.config.enabled:
            raise ObjectStorageError("Object storage is not configured.")

        try:
            self.internal_client.delete_object(Bucket=self.config.bucket, Key=file_key)
        except (ClientError, BotoCoreError) as exc:
            raise ObjectStorageError(f"Delete failed: {exc}") from exc
