from uuid import UUID

import boto3
import structlog
from botocore.exceptions import ClientError

from src.domain.repositories.avatar_storage import AvatarStorage

logger = structlog.get_logger()


class S3AvatarStorage(AvatarStorage):
    def __init__(self, bucket_name: str, region: str = "us-east-1") -> None:
        self._bucket_name = bucket_name
        self._region = region
        self._client = boto3.client("s3", region_name=region)

    async def upload(self, user_id: UUID, file_bytes: bytes, extension: str) -> str:
        key = f"avatars/{user_id}.{extension}"
        self._client.put_object(
            Bucket=self._bucket_name,
            Key=key,
            Body=file_bytes,
        )
        url = f"https://{self._bucket_name}.s3.{self._region}.amazonaws.com/{key}"
        logger.info("avatar.uploaded", user_id=str(user_id), key=key)
        return url

    async def delete(self, user_id: UUID, extension: str) -> None:
        key = f"avatars/{user_id}.{extension}"
        try:
            self._client.delete_object(Bucket=self._bucket_name, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return
            raise
        logger.info("avatar.deleted", user_id=str(user_id), key=key)
