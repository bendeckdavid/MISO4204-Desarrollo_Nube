"""Storage abstraction layer for local and S3 storage"""

import os

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageBackend:
    """Abstract storage backend"""

    def upload_file(self, file_data: bytes, file_path: str) -> str:
        """Upload file and return the storage path"""
        raise NotImplementedError

    def download_file(self, file_path: str) -> bytes:
        """Download file and return bytes"""
        raise NotImplementedError

    def delete_file(self, file_path: str) -> bool:
        """Delete file, return True if successful"""
        raise NotImplementedError

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        raise NotImplementedError

    def get_file_url(self, file_path: str) -> str:
        """Get URL or path to access file"""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Local filesystem storage"""

    def upload_file(self, file_data: bytes, file_path: str) -> str:
        """Upload file to local filesystem"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write file
        with open(file_path, "wb") as f:
            f.write(file_data)

        return file_path

    def download_file(self, file_path: str) -> bytes:
        """Download file from local filesystem"""
        with open(file_path, "rb") as f:
            return f.read()

    def delete_file(self, file_path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in local filesystem"""
        return os.path.exists(file_path)

    def get_file_url(self, file_path: str) -> str:
        """Return local file path"""
        return file_path


class S3Storage(StorageBackend):
    """AWS S3 storage using IAM Role (no explicit credentials needed)"""

    def __init__(self):
        """Initialize S3 client using IAM Role credentials"""
        # Boto3 automatically uses IAM Role from EC2 instance metadata
        # No need to pass access_key_id or secret_access_key
        self.s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
        self.bucket = settings.AWS_S3_BUCKET

    def upload_file(self, file_data: bytes, file_path: str) -> str:
        """Upload file to S3"""
        try:
            # Use the file_path as the S3 key (already includes prefix)
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_path,
                Body=file_data,
                ContentType=self._get_content_type(file_path),
            )
            return file_path
        except ClientError as e:
            raise Exception(f"Failed to upload to S3: {str(e)}")

    def download_file(self, file_path: str) -> bytes:
        """Download file from S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=file_path)
            return response["Body"].read()
        except ClientError as e:
            raise Exception(f"Failed to download from S3: {str(e)}")

    def delete_file(self, file_path: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=file_path)
            return True
        except ClientError:
            return False

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=file_path)
            return True
        except ClientError:
            return False

    def get_file_url(self, file_path: str) -> str:
        """Get S3 URL for file"""
        return f"s3://{self.bucket}/{file_path}"

    def get_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """Generate presigned URL for temporary access"""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": file_path},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

    def _get_content_type(self, file_path: str) -> str:
        """Determine content type based on file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }
        return content_types.get(ext, "application/octet-stream")


# Factory function to get the appropriate storage backend
def get_storage() -> StorageBackend:
    """Get storage backend based on configuration"""
    if settings.STORAGE_BACKEND == "s3":
        if not settings.AWS_S3_BUCKET:
            raise ValueError("AWS_S3_BUCKET must be set when using S3 storage")
        return S3Storage()
    else:
        return LocalStorage()


# Global storage instance
storage = get_storage()
