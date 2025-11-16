"""Tests for video processing worker functions"""
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.worker.videos import (
    _cleanup_temp_files,
    ensure_directory_exists,
    process_video_sync,
    resolve_container_path,
)


class TestResolveContainerPath:
    """Tests for resolve_container_path function"""

    def test_resolve_existing_absolute_path(self, tmp_path):
        """Test resolving an existing absolute path"""
        test_file = tmp_path / "test.mp4"
        test_file.write_text("test content")

        result = resolve_container_path(str(test_file))
        assert result == str(test_file)

    def test_resolve_non_existing_path_with_fallback(self, tmp_path):
        """Test resolving non-existing path with fallback"""
        # Create fallback directory structure
        fallback_dir = tmp_path / "fallback"
        fallback_dir.mkdir()

        # Create nested directory in fallback
        nested_dir = fallback_dir / "absolute" / "path"
        nested_dir.mkdir(parents=True)

        # Create file in nested directory
        test_file = nested_dir / "test.mp4"
        test_file.write_text("test content")

        # Try to resolve with absolute path that doesn't exist
        non_existing = "/absolute/path/test.mp4"
        result = resolve_container_path(non_existing, str(fallback_dir))
        assert result == str(test_file)

    def test_resolve_path_not_found(self):
        """Test resolving path that doesn't exist anywhere"""
        with pytest.raises(FileNotFoundError, match="File not found"):
            resolve_container_path("/non/existing/path.mp4")


class TestEnsureDirectoryExists:
    """Tests for ensure_directory_exists function"""

    def test_ensure_directory_exists_success(self, tmp_path):
        """Test creating directory successfully"""
        test_dir = tmp_path / "new_dir" / "subdir"
        test_file = test_dir / "test.mp4"

        result = ensure_directory_exists(str(test_file))
        assert result == str(test_file)
        assert test_dir.exists()

    def test_ensure_directory_exists_with_existing_dir(self, tmp_path):
        """Test with already existing directory"""
        test_dir = tmp_path / "existing_dir"
        test_dir.mkdir()
        test_file = test_dir / "test.mp4"

        result = ensure_directory_exists(str(test_file))
        assert result == str(test_file)

    @patch("app.worker.videos.os.makedirs")
    def test_ensure_directory_exists_permission_error_fallback(self, mock_makedirs, tmp_path):
        """Test fallback when permission denied"""
        test_file = "/restricted/path/test.mp4"
        fallback_dir = str(tmp_path / "fallback")

        # First call raises PermissionError, second succeeds
        mock_makedirs.side_effect = [PermissionError(), None]

        result = ensure_directory_exists(test_file, fallback_dir)
        expected = str(tmp_path / "fallback" / "restricted" / "path" / "test.mp4")
        assert result == expected

    @patch("app.worker.videos.os.makedirs")
    def test_ensure_directory_exists_permission_error_non_absolute(self, mock_makedirs):
        """Test permission error with non-absolute path (should re-raise)"""
        test_file = "relative/path/test.mp4"

        mock_makedirs.side_effect = PermissionError()

        with pytest.raises(PermissionError):
            ensure_directory_exists(test_file)


class TestCleanupTempFiles:
    """Tests for _cleanup_temp_files function"""

    def test_cleanup_existing_files(self, tmp_path):
        """Test cleaning up existing temp files"""
        temp1 = tmp_path / "temp1.mp4"
        temp2 = tmp_path / "temp2.mp4"
        temp1.write_text("temp content 1")
        temp2.write_text("temp content 2")

        _cleanup_temp_files(str(temp1), str(temp2))

        assert not temp1.exists()
        assert not temp2.exists()

    def test_cleanup_non_existing_files(self):
        """Test cleaning up non-existing files (should not raise)"""
        _cleanup_temp_files("/non/existing/temp1.mp4", "/non/existing/temp2.mp4")
        # Should complete without error

    def test_cleanup_with_none_values(self):
        """Test cleanup with None values"""
        _cleanup_temp_files(None, None)
        # Should complete without error

    @patch("app.worker.videos.os.unlink")
    @patch("app.worker.videos.os.path.exists")
    def test_cleanup_with_exception(self, mock_exists, mock_unlink, tmp_path):
        """Test cleanup when unlink raises exception"""
        temp1 = str(tmp_path / "temp1.mp4")
        temp2 = str(tmp_path / "temp2.mp4")

        # Mock exists to return True
        mock_exists.return_value = True

        # Mock unlink to raise exception
        mock_unlink.side_effect = PermissionError("Cannot delete")

        # Should not raise exception
        _cleanup_temp_files(temp1, temp2)

        # Verify unlink was attempted
        assert mock_unlink.call_count == 2


class TestProcessVideoSync:
    """Tests for process_video_sync function"""

    @patch("app.worker.videos._cleanup_temp_files")
    @patch("app.worker.videos._process_video_file")
    @patch("app.worker.videos._setup_file_paths")
    @patch("app.worker.videos.SessionLocal")
    @patch("app.worker.videos.settings")
    def test_process_video_sync_success_local(
        self,
        mock_settings,
        mock_session_local,
        mock_setup,
        mock_process,
        mock_cleanup,
        tmp_path,
    ):
        """Test successful video processing with local storage"""
        # Mock settings
        mock_settings.STORAGE_BACKEND = "local"

        # Mock database session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Mock video object
        mock_video = Mock()
        mock_video.id = "video123"
        mock_video.status = "pending"
        mock_video.original_file_path = str(tmp_path / "orig.mp4")
        mock_video.processed_file_path = str(tmp_path / "proc.mp4")

        mock_db.query.return_value.filter.return_value.first.return_value = mock_video

        # Mock setup file paths
        orig_path = str(tmp_path / "orig.mp4")
        proc_path = str(tmp_path / "proc.mp4")
        mock_setup.return_value = (orig_path, proc_path, None, None)

        result = process_video_sync("video123")

        assert result["status"] == "success"
        assert mock_video.status == "processed"
        assert mock_video.is_published is True
        mock_db.commit.assert_called()

    @patch("app.worker.videos._cleanup_temp_files")
    @patch("app.worker.videos.SessionLocal")
    def test_process_video_sync_video_not_found(self, mock_session_local, mock_cleanup):
        """Test processing when video is not found"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = process_video_sync("nonexistent")

        assert result["status"] == "failed"
        assert result["error"] == "Video not found"

    @patch("app.worker.videos._cleanup_temp_files")
    @patch("app.worker.videos._setup_file_paths")
    @patch("app.worker.videos.SessionLocal")
    def test_process_video_sync_processing_error(
        self, mock_session_local, mock_setup, mock_cleanup
    ):
        """Test processing when an error occurs"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_video = Mock()
        mock_video.id = "video123"
        mock_video.status = "pending"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video

        # Make setup raise an exception
        mock_setup.side_effect = Exception("Processing failed")

        result = process_video_sync("video123")

        assert result["status"] == "failed"
        assert "Processing failed" in result["error"]
