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
