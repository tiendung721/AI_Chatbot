from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .common import AppError
from .config import settings


def storage_client() -> Any:
    cfg = settings()
    return boto3.client(
        "s3",
        endpoint_url=cfg.s3_endpoint,
        aws_access_key_id=cfg.s3_access_key_id.get_secret_value(),
        aws_secret_access_key=cfg.s3_secret_access_key.get_secret_value(),
        region_name="us-east-1",
        config=Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 2}),
    )


def put_private(key: str, data: bytes, mime: str) -> None:
    storage_client().put_object(
        Bucket=settings().s3_bucket,
        Key=key,
        Body=data,
        ContentType=mime,
        Tagging="scan=pending",
        ContentDisposition="attachment",
    )


def get_private(key: str) -> bytes:
    response = storage_client().get_object(Bucket=settings().s3_bucket, Key=key)
    maximum = settings().max_upload_mb * 1024 * 1024
    body = response["Body"]
    try:
        if response["ContentLength"] > maximum:
            raise AppError("FILE_TOO_LARGE", "File vượt giới hạn xử lý.", 413)
        data = body.read(maximum + 1)
        if len(data) > maximum:
            raise AppError("FILE_TOO_LARGE", "File vượt giới hạn xử lý.", 413)
        return data
    finally:
        body.close()


def delete_private(key: str) -> None:
    storage_client().delete_object(Bucket=settings().s3_bucket, Key=key)


def mark_clean(key: str) -> None:
    storage_client().put_object_tagging(
        Bucket=settings().s3_bucket, Key=key, Tagging={"TagSet": [{"Key": "scan", "Value": "clean"}]}
    )


def initialize_storage() -> None:
    cfg = settings()
    client = boto3.client(
        "s3",
        endpoint_url=cfg.s3_endpoint,
        aws_access_key_id=cfg.s3_access_key_id.get_secret_value(),
        aws_secret_access_key=cfg.s3_secret_access_key.get_secret_value(),
        region_name="us-east-1",
    )
    try:
        client.head_bucket(Bucket=cfg.s3_bucket)
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in {"404", "NoSuchBucket"}:
            raise
        client.create_bucket(Bucket=cfg.s3_bucket)
    # No anonymous bucket policy or public ACL is ever applied.
    acl = client.get_bucket_acl(Bucket=cfg.s3_bucket)
    if any("AllUsers" in str(grant) or "AuthenticatedUsers" in str(grant) for grant in acl.get("Grants", [])):
        raise RuntimeError("Object bucket must be private")
    try:
        policy = client.get_bucket_policy(Bucket=cfg.s3_bucket)
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in {"NoSuchBucketPolicy", "NoSuchPolicy", "404"}:
            raise
    else:
        # This application never needs a bucket policy; fail closed on unexpected grants.
        if policy.get("Policy"):
            raise RuntimeError("Unexpected bucket policy; require operator review")
