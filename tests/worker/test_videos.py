"""Tests for video processing worker"""
import os
import tempfile
from unittest.mock import patch

import pytest

from app.worker.videos import resolve_container_path, ensure_directory_exists


class TestResolveContainerPath:
    """Tests for resolve_container_path function"""

    def test_resolve_existing_file(self):
        """Test resolving path for existing file"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = resolve_container_path(tmp_path)
            assert result == tmp_path
            assert os.path.exists(result)
        finally:
            os.unlink(tmp_path)

    def test_resolve_with_fallback(self):
        """Test resolving path with fallback directory"""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file in subdirectory
            subdir = os.path.join(tmpdir, "media", "uploads")
            os.makedirs(subdir, exist_ok=True)
            test_file = os.path.join(subdir, "test.mp4")

            with open(test_file, "w") as f:
                f.write("test")

            # Try to resolve with absolute path that doesn't exist directly
            # but exists relative to fallback
            abs_path = "/media/uploads/test.mp4"
            result = resolve_container_path(abs_path, fallback_base_dir=tmpdir)

            assert result == test_file
            assert os.path.exists(result)

    def test_resolve_nonexistent_file_raises_error(self):
        """Test that nonexistent file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            resolve_container_path("/nonexistent/path/to/file.mp4")


class TestEnsureDirectoryExists:
    """Tests for ensure_directory_exists function"""

    def test_ensure_directory_creates_path(self):
        """Test that directory is created for file path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "new", "subdir", "file.mp4")
            result = ensure_directory_exists(file_path)

            assert result == file_path
            assert os.path.exists(os.path.dirname(file_path))

    def test_ensure_directory_with_existing_path(self):
        """Test with already existing directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "file.mp4")
            result = ensure_directory_exists(file_path)

            assert result == file_path
            assert os.path.exists(tmpdir)

    def test_ensure_directory_with_fallback(self):
        """Test fallback when permission error occurs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock os.makedirs to raise PermissionError on first call
            original_makedirs = os.makedirs

            call_count = [0]

            def mock_makedirs(path, exist_ok=False):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise PermissionError("Permission denied")
                return original_makedirs(path, exist_ok=exist_ok)

            with patch("app.worker.videos.os.makedirs", side_effect=mock_makedirs):
                file_path = "/restricted/path/file.mp4"
                result = ensure_directory_exists(file_path, fallback_base_dir=tmpdir)

                # Should return fallback path
                assert tmpdir in result
                assert "restricted/path/file.mp4" in result

    def test_ensure_directory_permission_error_no_fallback(self):
        """Test permission error with relative path (no fallback)"""
        with patch("app.worker.videos.os.makedirs") as mock_makedirs:
            mock_makedirs.side_effect = PermissionError("Permission denied")

            with pytest.raises(PermissionError):
                ensure_directory_exists("relative/path/file.mp4")


class TestSetupFilePaths:
    """Tests for _setup_file_paths function"""

    @patch("app.worker.videos.storage")
    @patch("app.worker.videos.tempfile.NamedTemporaryFile")
    def test_setup_file_paths_s3(self, mock_temp, mock_storage):
        """Test file paths setup for S3 storage"""
        from app.worker.videos import _setup_file_paths
        from app.db import models
        from unittest.mock import Mock, MagicMock

        # Mock temp files
        mock_orig = MagicMock()
        mock_orig.name = "/tmp/orig.mp4"
        mock_orig.__enter__ = Mock(return_value=mock_orig)
        mock_orig.__exit__ = Mock(return_value=False)

        mock_proc = MagicMock()
        mock_proc.name = "/tmp/proc.mp4"
        mock_proc.__enter__ = Mock(return_value=mock_proc)
        mock_proc.__exit__ = Mock(return_value=False)

        mock_temp.side_effect = [mock_orig, mock_proc]
        mock_storage.download_file.return_value = b"video data"

        # Mock video and settings
        video = Mock(spec=models.Video)
        video.original_file_path = "uploads/test.mp4"

        settings_mock = Mock()
        settings_mock.STORAGE_BACKEND = "s3"

        # Call function
        orig, proc, temp_orig, temp_proc = _setup_file_paths(video, settings_mock)

        assert orig == "/tmp/orig.mp4"
        assert proc == "/tmp/proc.mp4"
        assert temp_orig == "/tmp/orig.mp4"
        assert temp_proc == "/tmp/proc.mp4"
        mock_storage.download_file.assert_called_once_with("uploads/test.mp4")

    @patch("app.worker.videos.ensure_directory_exists")
    @patch("app.worker.videos.resolve_container_path")
    @patch("app.worker.videos.os.access")
    def test_setup_file_paths_local(self, mock_access, mock_resolve, mock_ensure):
        """Test file paths setup for local storage"""
        from app.worker.videos import _setup_file_paths
        from app.db import models
        from unittest.mock import Mock

        # Mock video and settings
        video = Mock(spec=models.Video)
        video.original_file_path = "/app/media/uploads/test.mp4"
        video.processed_file_path = "/app/media/processed/test.mp4"

        settings_mock = Mock()
        settings_mock.STORAGE_BACKEND = "local"
        settings_mock.APP_BASE_DIR = "/app"

        mock_resolve.return_value = "/app/media/uploads/test.mp4"
        mock_access.return_value = True
        mock_ensure.return_value = "/app/media/processed/test.mp4"

        # Call function
        orig, proc, temp_orig, temp_proc = _setup_file_paths(video, settings_mock)

        assert orig == "/app/media/uploads/test.mp4"
        assert proc == "/app/media/processed/test.mp4"
        assert temp_orig is None
        assert temp_proc is None

    @patch("app.worker.videos.resolve_container_path")
    @patch("app.worker.videos.os.access")
    def test_setup_file_paths_local_permission_error(self, mock_access, mock_resolve):
        """Test permission error for local storage"""
        from app.worker.videos import _setup_file_paths
        from app.db import models
        from unittest.mock import Mock

        video = Mock(spec=models.Video)
        video.original_file_path = "/app/media/uploads/test.mp4"

        settings_mock = Mock()
        settings_mock.STORAGE_BACKEND = "local"
        settings_mock.APP_BASE_DIR = "/app"

        mock_resolve.return_value = "/app/media/uploads/test.mp4"
        mock_access.return_value = False  # No read permission

        with pytest.raises(PermissionError):
            _setup_file_paths(video, settings_mock)


class TestProcessVideoFile:
    """Tests for _process_video_file function"""

    @patch("app.worker.videos.CompositeVideoClip")
    @patch("app.worker.videos.TextClip")
    @patch("app.worker.videos.VideoFileClip")
    def test_process_video_file_success(self, mock_video_clip, mock_text_clip, mock_composite):
        """Test successful video processing"""
        from app.worker.videos import _process_video_file
        from unittest.mock import MagicMock

        # Mock video clips
        original_clip_mock = MagicMock()
        original_clip_mock.duration = 60
        original_clip_mock.subclipped.return_value = original_clip_mock
        original_clip_mock.resized.return_value = original_clip_mock
        mock_video_clip.return_value = original_clip_mock

        watermark_mock = MagicMock()
        watermark_mock.with_position.return_value = watermark_mock
        watermark_mock.with_duration.return_value = watermark_mock
        mock_text_clip.return_value = watermark_mock

        final_clip_mock = MagicMock()
        mock_composite.return_value = final_clip_mock

        # Process
        _process_video_file("/tmp/orig.mp4", "/tmp/proc.mp4")

        # Verify calls
        mock_video_clip.assert_called_once_with("/tmp/orig.mp4")
        original_clip_mock.subclipped.assert_called_once_with(0, 30)
        original_clip_mock.resized.assert_called_once_with(height=720)
        final_clip_mock.write_videofile.assert_called_once()
        final_clip_mock.close.assert_called_once()


class TestCleanupTempFiles:
    """Tests for _cleanup_temp_files function"""

    @patch("app.worker.videos.os.unlink")
    @patch("app.worker.videos.os.path.exists")
    def test_cleanup_both_files(self, mock_exists, mock_unlink):
        """Test cleanup of both temporary files"""
        from app.worker.videos import _cleanup_temp_files

        mock_exists.return_value = True

        _cleanup_temp_files("/tmp/orig.mp4", "/tmp/proc.mp4")

        assert mock_unlink.call_count == 2

    @patch("app.worker.videos.os.unlink")
    @patch("app.worker.videos.os.path.exists")
    def test_cleanup_none_files(self, mock_exists, mock_unlink):
        """Test cleanup with None files"""
        from app.worker.videos import _cleanup_temp_files

        _cleanup_temp_files(None, None)

        mock_unlink.assert_not_called()

    @patch("app.worker.videos.os.unlink")
    @patch("app.worker.videos.os.path.exists")
    def test_cleanup_with_exception(self, mock_exists, mock_unlink):
        """Test cleanup handles exceptions gracefully"""
        from app.worker.videos import _cleanup_temp_files

        mock_exists.return_value = True
        mock_unlink.side_effect = Exception("Cleanup error")

        # Should not raise exception
        _cleanup_temp_files("/tmp/orig.mp4", "/tmp/proc.mp4")


class TestProcessVideoTask:
    """Tests for process_video Celery task"""

    @patch("app.worker.videos._cleanup_temp_files")
    @patch("app.worker.videos.storage")
    @patch("app.worker.videos._process_video_file")
    @patch("app.worker.videos._setup_file_paths")
    @patch("app.worker.videos.SessionLocal")
    @patch("app.worker.videos.process_video.retry")
    def test_process_video_success_s3(
        self, mock_retry, mock_session, mock_setup, mock_process, mock_storage, mock_cleanup
    ):
        """Test successful video processing with S3"""
        from app.worker.videos import process_video
        from app.db import models
        from unittest.mock import Mock, MagicMock, mock_open

        # Mock database session
        db_mock = MagicMock()
        mock_session.return_value = db_mock

        # Mock video
        video_mock = Mock(spec=models.Video)
        video_mock.id = "test-id"
        video_mock.status = "pending"
        video_mock.processed_file_path = "processed/test.mp4"
        db_mock.query().filter().first.return_value = video_mock

        # Mock settings
        with patch("app.worker.videos.settings") as mock_settings:
            mock_settings.STORAGE_BACKEND = "s3"

            # Mock file paths setup
            mock_setup.return_value = (
                "/tmp/orig.mp4",
                "/tmp/proc.mp4",
                "/tmp/orig.mp4",
                "/tmp/proc.mp4",
            )

            # Mock file open
            with patch("builtins.open", mock_open(read_data=b"processed video")):
                # Call task with Celery run method
                result = process_video.run("test-id")

        assert result["status"] == "success"
        assert video_mock.status == "processed"
        assert video_mock.is_published is True
        mock_storage.upload_file.assert_called_once()
        mock_cleanup.assert_called_once()

    @patch("app.worker.videos._cleanup_temp_files")
    @patch("app.worker.videos._process_video_file")
    @patch("app.worker.videos._setup_file_paths")
    @patch("app.worker.videos.SessionLocal")
    @patch("app.worker.videos.process_video.retry")
    def test_process_video_success_local(
        self, mock_retry, mock_session, mock_setup, mock_process, mock_cleanup
    ):
        """Test successful video processing with local storage"""
        from app.worker.videos import process_video
        from app.db import models
        from unittest.mock import Mock, MagicMock

        # Mock database session
        db_mock = MagicMock()
        mock_session.return_value = db_mock

        # Mock video
        video_mock = Mock(spec=models.Video)
        video_mock.id = "test-id"
        video_mock.status = "pending"
        db_mock.query().filter().first.return_value = video_mock

        # Mock settings
        with patch("app.worker.videos.settings") as mock_settings:
            mock_settings.STORAGE_BACKEND = "local"

            # Mock file paths setup
            mock_setup.return_value = ("/app/orig.mp4", "/app/proc.mp4", None, None)

            # Call task with Celery run method
            result = process_video.run("test-id")

        assert result["status"] == "success"
        assert video_mock.status == "processed"
        mock_cleanup.assert_called_once()

    @patch("app.worker.videos._cleanup_temp_files")
    @patch("app.worker.videos.SessionLocal")
    @patch("app.worker.videos.process_video.retry")
    def test_process_video_not_found(self, mock_retry, mock_session, mock_cleanup):
        """Test processing video that doesn't exist"""
        from app.worker.videos import process_video
        from unittest.mock import MagicMock

        # Mock database session
        db_mock = MagicMock()
        mock_session.return_value = db_mock
        db_mock.query().filter().first.return_value = None

        # Call task with Celery run method
        result = process_video.run("nonexistent-id")

        assert result["status"] == "failed"
        assert "Video not found" in result["error"]
        mock_cleanup.assert_called_once()

    @patch("app.worker.videos._cleanup_temp_files")
    @patch("app.worker.videos._setup_file_paths")
    @patch("app.worker.videos.SessionLocal")
    def test_process_video_error_with_retry(self, mock_session, mock_setup, mock_cleanup):
        """Test video processing error triggers retry"""
        from app.worker.videos import process_video
        from app.db import models
        from unittest.mock import Mock, MagicMock

        # Mock database session
        db_mock = MagicMock()
        mock_session.return_value = db_mock

        # Mock video
        video_mock = Mock(spec=models.Video)
        video_mock.id = "test-id"
        video_mock.status = "pending"
        db_mock.query().filter().first.return_value = video_mock

        # Mock setup to raise error
        mock_setup.side_effect = Exception("Processing error")

        # Mock retry to raise exception (simulating retry behavior)
        with patch.object(process_video, "retry", side_effect=Exception("Retry triggered")):
            # Call task and expect retry exception
            with pytest.raises(Exception) as exc_info:
                process_video.run("test-id")

        assert "Retry triggered" in str(exc_info.value)
        assert video_mock.status == "failed"
        mock_cleanup.assert_called_once()
