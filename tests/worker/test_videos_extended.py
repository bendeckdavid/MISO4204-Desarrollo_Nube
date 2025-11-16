"""Extended tests for video processing worker to achieve 100% coverage"""
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.worker.videos import _setup_file_paths, process_video_sync


class TestSetupFilePathsExtended:
    """Extended tests for _setup_file_paths function"""

    @patch("app.worker.videos.tempfile.NamedTemporaryFile")
    @patch("app.worker.videos.storage")
    def test_setup_file_paths_s3_with_write(self, mock_storage, mock_tempfile):
        """Test S3 setup with actual file writes"""
        # Mock settings
        mock_settings = Mock()
        mock_settings.STORAGE_BACKEND = "s3"
        mock_settings.APP_BASE_DIR = "/app"

        # Mock video
        mock_video = Mock()
        mock_video.original_file_path = "uploads/test.mp4"
        mock_video.processed_file_path = "processed/test.mp4"

        # Mock temp files
        mock_temp_orig = Mock()
        mock_temp_orig.name = "/tmp/orig.mp4"
        mock_temp_orig.write = Mock()
        mock_temp_orig.flush = Mock()

        mock_temp_proc = Mock()
        mock_temp_proc.name = "/tmp/proc.mp4"

        # Setup context managers
        mock_temp_orig.__enter__ = Mock(return_value=mock_temp_orig)
        mock_temp_orig.__exit__ = Mock(return_value=None)
        mock_temp_proc.__enter__ = Mock(return_value=mock_temp_proc)
        mock_temp_proc.__exit__ = Mock(return_value=None)

        mock_tempfile.side_effect = [mock_temp_orig, mock_temp_proc]

        # Mock storage download
        mock_storage.download_file.return_value = b"video content"

        result = _setup_file_paths(mock_video, mock_settings)

        assert result[0] == "/tmp/orig.mp4"
        assert result[1] == "/tmp/proc.mp4"
        assert result[2] == "/tmp/orig.mp4"
        assert result[3] == "/tmp/proc.mp4"
        mock_temp_orig.write.assert_called_once_with(b"video content")
        mock_temp_orig.flush.assert_called_once()

    def test_setup_file_paths_local_permission_error(self, tmp_path):
        """Test local setup with permission error fallback"""
        # Mock settings
        mock_settings = Mock()
        mock_settings.STORAGE_BACKEND = "local"
        mock_settings.APP_BASE_DIR = str(tmp_path)

        # Mock video
        mock_video = Mock()
        orig_file = tmp_path / "test.mp4"
        orig_file.write_text("content")
        mock_video.original_file_path = str(orig_file)
        mock_video.processed_file_path = str(tmp_path / "processed" / "test.mp4")

        with patch("app.worker.videos.resolve_container_path") as mock_resolve:
            mock_resolve.return_value = str(orig_file)

            with patch("app.worker.videos.ensure_directory_exists") as mock_ensure:
                mock_ensure.return_value = str(tmp_path / "processed" / "test.mp4")

                result = _setup_file_paths(mock_video, mock_settings)

                assert result[0] == str(orig_file)
                assert result[2] is None
                assert result[3] is None

    def test_setup_file_paths_local_no_read_permission(self, tmp_path):
        """Test local setup when file is not readable"""
        # Mock settings
        mock_settings = Mock()
        mock_settings.STORAGE_BACKEND = "local"
        mock_settings.APP_BASE_DIR = str(tmp_path)

        # Mock video
        mock_video = Mock()
        orig_file = tmp_path / "test.mp4"
        orig_file.write_text("content")
        mock_video.original_file_path = str(orig_file)
        mock_video.processed_file_path = str(tmp_path / "processed" / "test.mp4")

        with patch("app.worker.videos.resolve_container_path") as mock_resolve:
            mock_resolve.return_value = str(orig_file)

            with patch("app.worker.videos.os.access") as mock_access:
                # Mock file as not readable
                mock_access.return_value = False

                with pytest.raises(PermissionError, match="Cannot read original video file"):
                    _setup_file_paths(mock_video, mock_settings)


class TestProcessVideoSyncExtended:
    """Extended tests for process_video_sync function"""

    @patch("app.worker.videos._cleanup_temp_files")
    @patch("app.worker.videos._process_video_file")
    @patch("app.worker.videos._setup_file_paths")
    @patch("app.worker.videos.storage")
    @patch("app.worker.videos.SessionLocal")
    @patch("app.worker.videos.settings")
    def test_process_video_sync_s3_backend(
        self,
        mock_settings,
        mock_session_local,
        mock_storage,
        mock_setup,
        mock_process,
        mock_cleanup,
        tmp_path,
    ):
        """Test video processing with S3 backend"""
        # Mock settings
        mock_settings.STORAGE_BACKEND = "s3"

        # Mock database
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Mock video
        mock_video = Mock()
        mock_video.id = "video123"
        mock_video.status = "pending"
        mock_video.processed_file_path = "s3://bucket/processed/video123.mp4"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_video

        # Mock setup file paths to return temp files
        temp_orig = str(tmp_path / "temp_orig.mp4")
        temp_proc = str(tmp_path / "temp_proc.mp4")
        (tmp_path / "temp_proc.mp4").write_text("processed content")

        mock_setup.return_value = (temp_orig, temp_proc, temp_orig, temp_proc)

        # Mock storage upload
        mock_storage.upload_file.return_value = None

        result = process_video_sync("video123")

        assert result["status"] == "success"
        assert mock_video.status == "processed"
        # Verify file was uploaded to S3
        mock_storage.upload_file.assert_called_once()

    @patch("app.worker.videos._cleanup_temp_files")
    @patch("app.worker.videos._process_video_file")
    @patch("app.worker.videos._setup_file_paths")
    @patch("app.worker.videos.SessionLocal")
    def test_process_video_sync_db_error_on_status_update(
        self, mock_session_local, mock_setup, mock_process, mock_cleanup
    ):
        """Test handling of database error when updating status to failed"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # First call returns video, second call (in except block) returns None
        mock_video = Mock()
        mock_video.id = "video123"
        mock_video.status = "pending"

        # Make query fail on second call in except block
        call_count = [0]

        def query_side_effect(*args):
            result = Mock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.filter.return_value.first.return_value = mock_video
            else:
                # Simulate DB error on second query
                result.filter.return_value.first.side_effect = Exception("DB error")
            return result

        mock_db.query.side_effect = query_side_effect

        # Make setup raise exception
        mock_setup.side_effect = Exception("Processing failed")

        result = process_video_sync("video123")

        assert result["status"] == "failed"
        assert "Processing failed" in result["error"]
