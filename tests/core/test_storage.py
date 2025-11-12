"""Tests for storage abstraction layer"""
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.core.storage import (
    LocalStorage,
    S3Storage,
    StorageDownloadError,
    StorageUploadError,
    StorageURLError,
    get_storage,
)


class TestLocalStorage:
    """Tests for LocalStorage backend"""

    def test_upload_file_success(self):
        """Test successful file upload to local filesystem"""
        storage = LocalStorage()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "subdir", "test.mp4")
            file_data = b"test video content"

            result = storage.upload_file(file_data, file_path)

            assert result == file_path
            assert os.path.exists(file_path)
            with open(file_path, "rb") as f:
                assert f.read() == file_data

    def test_download_file_success(self):
        """Test successful file download from local filesystem"""
        storage = LocalStorage()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name

        try:
            result = storage.download_file(tmp_path)
            assert result == b"test content"
        finally:
            os.unlink(tmp_path)

    def test_delete_file_success(self):
        """Test successful file deletion"""
        storage = LocalStorage()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        assert os.path.exists(tmp_path)
        result = storage.delete_file(tmp_path)

        assert result is True
        assert not os.path.exists(tmp_path)

    def test_delete_file_not_found(self):
        """Test deleting non-existent file returns False"""
        storage = LocalStorage()

        result = storage.delete_file("/nonexistent/file.mp4")

        assert result is False

    def test_delete_file_with_exception(self):
        """Test delete_file handles exceptions gracefully"""
        storage = LocalStorage()

        with patch("os.path.exists", return_value=True):
            with patch("os.remove", side_effect=Exception("Permission denied")):
                result = storage.delete_file("/some/file.mp4")

                assert result is False

    def test_file_exists_true(self):
        """Test file_exists returns True for existing file"""
        storage = LocalStorage()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = storage.file_exists(tmp_path)
            assert result is True
        finally:
            os.unlink(tmp_path)

    def test_file_exists_false(self):
        """Test file_exists returns False for non-existent file"""
        storage = LocalStorage()

        result = storage.file_exists("/nonexistent/file.mp4")

        assert result is False

    def test_get_file_url(self):
        """Test get_file_url returns the file path"""
        storage = LocalStorage()

        file_path = "/uploads/test.mp4"
        result = storage.get_file_url(file_path)

        assert result == file_path


class TestS3Storage:
    """Tests for S3Storage backend"""

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_init_success(self, mock_settings, mock_boto_client):
        """Test S3Storage initialization"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"

        storage = S3Storage()

        mock_boto_client.assert_called_once_with("s3", region_name="us-east-1")
        assert storage.bucket == "test-bucket"

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_upload_file_success(self, mock_settings, mock_boto_client):
        """Test successful file upload to S3"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        storage = S3Storage()
        file_data = b"test content"
        file_path = "uploads/test.mp4"

        result = storage.upload_file(file_data, file_path)

        assert result == file_path
        mock_s3_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key=file_path,
            Body=file_data,
            ContentType="video/mp4",
        )

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_upload_file_client_error(self, mock_settings, mock_boto_client):
        """Test upload_file raises StorageUploadError on ClientError"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "PutObject"
        )

        storage = S3Storage()

        with pytest.raises(StorageUploadError) as exc_info:
            storage.upload_file(b"data", "test.mp4")

        assert "Failed to upload to S3" in str(exc_info.value)

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_download_file_success(self, mock_settings, mock_boto_client):
        """Test successful file download from S3"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        mock_body = MagicMock()
        mock_body.read.return_value = b"test content"
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        storage = S3Storage()
        result = storage.download_file("uploads/test.mp4")

        assert result == b"test content"
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="uploads/test.mp4"
        )

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_download_file_client_error(self, mock_settings, mock_boto_client):
        """Test download_file raises StorageDownloadError on ClientError"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )

        storage = S3Storage()

        with pytest.raises(StorageDownloadError) as exc_info:
            storage.download_file("nonexistent.mp4")

        assert "Failed to download from S3" in str(exc_info.value)

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_delete_file_success(self, mock_settings, mock_boto_client):
        """Test successful file deletion from S3"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        storage = S3Storage()
        result = storage.delete_file("uploads/test.mp4")

        assert result is True
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="uploads/test.mp4"
        )

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_delete_file_client_error(self, mock_settings, mock_boto_client):
        """Test delete_file returns False on ClientError"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "DeleteObject"
        )

        storage = S3Storage()
        result = storage.delete_file("test.mp4")

        assert result is False

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_file_exists_true(self, mock_settings, mock_boto_client):
        """Test file_exists returns True when file exists in S3"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        storage = S3Storage()
        result = storage.file_exists("uploads/test.mp4")

        assert result is True
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="uploads/test.mp4"
        )

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_file_exists_false(self, mock_settings, mock_boto_client):
        """Test file_exists returns False on ClientError"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )

        storage = S3Storage()
        result = storage.file_exists("nonexistent.mp4")

        assert result is False

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_get_file_url(self, mock_settings, mock_boto_client):
        """Test get_file_url returns S3 URL"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_boto_client.return_value = MagicMock()

        storage = S3Storage()
        result = storage.get_file_url("uploads/test.mp4")

        assert result == "s3://test-bucket/uploads/test.mp4"

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_get_presigned_url_success(self, mock_settings, mock_boto_client):
        """Test successful presigned URL generation"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.generate_presigned_url.return_value = "https://presigned-url.com"

        storage = S3Storage()
        result = storage.get_presigned_url("uploads/test.mp4", expiration=3600)

        assert result == "https://presigned-url.com"
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "uploads/test.mp4"},
            ExpiresIn=3600,
        )

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_get_presigned_url_client_error(self, mock_settings, mock_boto_client):
        """Test get_presigned_url raises StorageURLError on ClientError"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "GeneratePresignedUrl"
        )

        storage = S3Storage()

        with pytest.raises(StorageURLError) as exc_info:
            storage.get_presigned_url("test.mp4")

        assert "Failed to generate presigned URL" in str(exc_info.value)

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_get_content_type_mp4(self, mock_settings, mock_boto_client):
        """Test _get_content_type for MP4 files"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_boto_client.return_value = MagicMock()

        storage = S3Storage()
        result = storage._get_content_type("test.mp4")

        assert result == "video/mp4"

    @patch("app.core.storage.boto3.client")
    @patch("app.core.storage.settings")
    def test_get_content_type_unknown(self, mock_settings, mock_boto_client):
        """Test _get_content_type for unknown file types"""
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_boto_client.return_value = MagicMock()

        storage = S3Storage()
        result = storage._get_content_type("test.unknown")

        assert result == "application/octet-stream"


class TestGetStorage:
    """Tests for get_storage factory function"""

    @patch("app.core.storage.settings")
    def test_get_storage_s3(self, mock_settings):
        """Test get_storage returns S3Storage when configured"""
        mock_settings.STORAGE_BACKEND = "s3"
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_settings.AWS_REGION = "us-east-1"

        with patch("app.core.storage.boto3.client"):
            storage = get_storage()

            assert isinstance(storage, S3Storage)

    @patch("app.core.storage.settings")
    def test_get_storage_s3_no_bucket(self, mock_settings):
        """Test get_storage raises ValueError when S3 bucket not set"""
        mock_settings.STORAGE_BACKEND = "s3"
        mock_settings.AWS_S3_BUCKET = None

        with pytest.raises(ValueError) as exc_info:
            get_storage()

        assert "AWS_S3_BUCKET must be set when using S3 storage" in str(exc_info.value)

    @patch("app.core.storage.settings")
    def test_get_storage_local(self, mock_settings):
        """Test get_storage returns LocalStorage when configured"""
        mock_settings.STORAGE_BACKEND = "local"

        storage = get_storage()

        assert isinstance(storage, LocalStorage)


class TestStorageBackend:
    """Tests for abstract StorageBackend class"""

    def test_upload_file_not_implemented(self):
        """Test upload_file raises NotImplementedError"""
        from app.core.storage import StorageBackend

        backend = StorageBackend()

        with pytest.raises(NotImplementedError):
            backend.upload_file(b"data", "path")

    def test_download_file_not_implemented(self):
        """Test download_file raises NotImplementedError"""
        from app.core.storage import StorageBackend

        backend = StorageBackend()

        with pytest.raises(NotImplementedError):
            backend.download_file("path")

    def test_delete_file_not_implemented(self):
        """Test delete_file raises NotImplementedError"""
        from app.core.storage import StorageBackend

        backend = StorageBackend()

        with pytest.raises(NotImplementedError):
            backend.delete_file("path")

    def test_file_exists_not_implemented(self):
        """Test file_exists raises NotImplementedError"""
        from app.core.storage import StorageBackend

        backend = StorageBackend()

        with pytest.raises(NotImplementedError):
            backend.file_exists("path")

    def test_get_file_url_not_implemented(self):
        """Test get_file_url raises NotImplementedError"""
        from app.core.storage import StorageBackend

        backend = StorageBackend()

        with pytest.raises(NotImplementedError):
            backend.get_file_url("path")
