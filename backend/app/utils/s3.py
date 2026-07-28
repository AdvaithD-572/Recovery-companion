# app/utils/s3.py

import uuid as uuid_module
import aioboto3
from app.core.config import settings


async def upload_to_s3(file_bytes: bytes, bucket: str, key_prefix: str, content_type: str) -> str:
    """
    Upload file to AWS S3.
    Returns the S3 key (path) of the uploaded file.
    """
    file_uuid = uuid_module.uuid4()
    ext = content_type.split("/")[-1]
    key = f"{key_prefix}/{file_uuid}.{ext}"

    session = aioboto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    async with session.client("s3") as s3:
        await s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
            ServerSideEncryption="aws:kms",
        )
    return key
