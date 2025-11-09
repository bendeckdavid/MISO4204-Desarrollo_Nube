"""Tests for video management endpoints"""
import io
from unittest.mock import patch
from fastapi import status
from fastapi.testclient import TestClient

from app.db import models
from app.core.security import create_access_token


class TestVideoUpload:
    """Tests for video upload endpoint"""

    @patch("app.api.routes.videos.process_video")
    @patch("app.api.routes.videos.storage")
    def test_upload_video_success(
        self,
        mock_storage,
        mock_process_video,
        client: TestClient,
        db,
    ):
        """Test successful video upload"""
        # Mock storage operations
        mock_storage.upload_file.return_value = "uploads/test_video.mp4"
        mock_storage.file_exists.return_value = True

        # Create and login user
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        # Create a fake video file
        fake_video = io.BytesIO(b"fake video content for testing")
        fake_video.name = "test_video.mp4"

        response = client.post(
            "/api/videos/upload",
            files={"file": ("test_video.mp4", fake_video, "video/mp4")},
            data={"title": "Mi mejor tiro"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "video_id" in data or "id" in data
        assert "user_id" in data or "title" in data

    def test_upload_video_without_auth(self, client: TestClient, db):
        """Test video upload without authentication"""
        fake_video = io.BytesIO(b"fake video content")
        response = client.post(
            "/api/videos/upload",
            files={"file": ("test.mp4", fake_video, "video/mp4")},
            data={"title": "Test"},
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_upload_video_missing_title(self, client: TestClient, db):
        """Test video upload without title"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        fake_video = io.BytesIO(b"fake video content")
        response = client.post(
            "/api/videos/upload",
            files={"file": ("test.mp4", fake_video, "video/mp4")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_video_invalid_file_type(self, client: TestClient, db):
        """Test video upload with invalid file type"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan2@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        # Upload a text file instead of video
        fake_file = io.BytesIO(b"this is not a video")
        response = client.post(
            "/api/videos/upload",
            files={"file": ("document.txt", fake_file, "text/plain")},
            data={"title": "Test Video"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "video format" in response.json()["detail"].lower()

    def test_upload_video_no_file(self, client: TestClient, db):
        """Test video upload without file"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan3@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        response = client.post(
            "/api/videos/upload",
            data={"title": "Test Video"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    @patch("app.api.routes.videos.process_video")
    @patch("app.api.routes.videos.storage")
    def test_upload_video_file_save_error(
        self,
        mock_storage,
        mock_process_video,
        client: TestClient,
        db,
    ):
        """Test video upload when file save fails"""
        # Mock storage operations to simulate file not being saved
        mock_storage.upload_file.return_value = "uploads/test_video.mp4"
        mock_storage.file_exists.return_value = False  # File doesn't exist after save

        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan_error@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        fake_file = io.BytesIO(b"fake video content")
        response = client.post(
            "/api/videos/upload",
            files={"file": ("test.mp4", fake_file, "video/mp4")},
            data={"title": "Test Video"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_upload_video_empty_filename(self, client: TestClient, db):
        """Test video upload with empty filename (returns 422 from FastAPI)"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan5@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        # Create file with empty filename
        fake_video = io.BytesIO(b"fake video content")
        fake_video.name = ""

        response = client.post(
            "/api/videos/upload",
            files={"file": ("", fake_video, "video/mp4")},
            data={"title": "Test Video"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # FastAPI returns 422 for empty filenames
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("app.api.routes.videos.process_video")
    @patch("app.api.routes.videos.storage")
    @patch("app.api.routes.videos.settings")
    def test_upload_video_file_size_exceeds_limit(
        self,
        mock_settings,
        mock_storage,
        mock_process_video,
        client: TestClient,
        db,
    ):
        """Test video upload when file size exceeds limit"""
        # Mock settings with small file size limit
        mock_settings.MAX_VIDEO_SIZE = 100
        mock_settings.STORAGE_BACKEND = "local"
        mock_settings.UPLOAD_BASE_DIR = "/uploads"
        mock_settings.PROCESSED_BASE_DIR = "/processed"

        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan6@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        # Create a file that exceeds the limit
        large_content = b"x" * 200  # 200 bytes > 100 bytes limit
        fake_video = io.BytesIO(large_content)
        fake_video.name = "large_video.mp4"

        response = client.post(
            "/api/videos/upload",
            files={"file": ("large_video.mp4", fake_video, "video/mp4")},
            data={"title": "Large Video"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "exceeds limit" in response.json()["detail"]

    @patch("app.api.routes.videos.process_video")
    @patch("app.api.routes.videos.storage")
    @patch("app.api.routes.videos.settings")
    def test_upload_video_s3_storage_backend(
        self,
        mock_settings,
        mock_storage,
        mock_process_video,
        client: TestClient,
        db,
    ):
        """Test video upload with S3 storage backend"""
        # Mock settings for S3
        mock_settings.STORAGE_BACKEND = "s3"
        mock_settings.S3_UPLOAD_PREFIX = "uploads/"
        mock_settings.S3_PROCESSED_PREFIX = "processed/"
        mock_settings.MAX_VIDEO_SIZE = 100 * 1024 * 1024

        # Mock storage operations
        mock_storage.upload_file.return_value = "uploads/test.mp4"
        mock_storage.file_exists.return_value = True

        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan7@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        fake_video = io.BytesIO(b"fake video content")
        fake_video.name = "test.mp4"

        response = client.post(
            "/api/videos/upload",
            files={"file": ("test.mp4", fake_video, "video/mp4")},
            data={"title": "S3 Test Video"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "video_id" in response.json()


class TestListMyVideos:
    """Tests for listing user's videos"""

    def test_list_my_videos_success(self, client: TestClient, db):
        """Test successful retrieval of user's videos"""
        # Create user
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create some videos for this user
        video1 = models.Video(
            title="Video 1",
            user_id=user.id,
            status="pending",
            original_file_path="/uploads/video1.mp4",
            processed_file_path="/processed/video1.mp4",
        )
        video2 = models.Video(
            title="Video 2",
            user_id=user.id,
            status="completed",
            original_file_path="/uploads/video2.mp4",
            processed_file_path="/processed/video2.mp4",
        )
        db.add_all([video1, video2])
        db.commit()

        token = create_access_token(data={"sub": str(user.id)})

        response = client.get(
            "/api/videos",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_my_videos_without_auth(self, client: TestClient, db):
        """Test listing videos without authentication"""
        response = client.get("/api/videos")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_list_my_videos_empty(self, client: TestClient, db):
        """Test listing videos when user has no videos"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        response = client.get(
            "/api/videos",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


class TestGetVideoDetail:
    """Tests for getting video detail"""

    def test_get_video_detail_success(self, client: TestClient, db):
        """Test successful retrieval of video detail"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        video = models.Video(
            title="Test Video",
            user_id=user.id,
            status="completed",
            original_file_path="/uploads/test.mp4",
            processed_file_path="/processed/test.mp4",
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        token = create_access_token(data={"sub": str(user.id)})

        response = client.get(
            f"/api/videos/{video.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Test Video"
        assert data["status"] == "completed"

    def test_get_video_detail_not_owner(self, client: TestClient, db):
        """Test getting video detail when user is not the owner"""
        owner = models.User(
            first_name="Owner",
            last_name="User",
            email="owner@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        other_user = models.User(
            first_name="Other",
            last_name="User",
            email="other@example.com",
            password="SecurePass123!",
            city="Bogotá",
            country="Colombia",
        )
        db.add_all([owner, other_user])
        db.commit()
        db.refresh(owner)
        db.refresh(other_user)

        video = models.Video(
            title="Owner's Video",
            user_id=owner.id,
            status="completed",
            original_file_path="/uploads/test.mp4",
            processed_file_path="/processed/test.mp4",
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        token = create_access_token(data={"sub": str(other_user.id)})

        response = client.get(
            f"/api/videos/{video.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_video_detail_not_found(self, client: TestClient, db):
        """Test getting non-existent video"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        import uuid

        fake_id = str(uuid.uuid4())

        response = client.get(
            f"/api/videos/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteVideo:
    """Tests for deleting videos"""

    def test_delete_video_success(self, client: TestClient, db):
        """Test successful video deletion"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        video = models.Video(
            title="Test Video",
            user_id=user.id,
            status="pending",
            original_file_path="/uploads/test.mp4",
            processed_file_path="/processed/test.mp4",
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        token = create_access_token(data={"sub": str(user.id)})

        response = client.delete(
            f"/api/videos/{video.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "eliminado" in data["message"].lower()

    def test_delete_video_not_owner(self, client: TestClient, db):
        """Test deleting video when user is not the owner"""
        owner = models.User(
            first_name="Owner",
            last_name="User",
            email="owner@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        other_user = models.User(
            first_name="Other",
            last_name="User",
            email="other@example.com",
            password="SecurePass123!",
            city="Bogotá",
            country="Colombia",
        )
        db.add_all([owner, other_user])
        db.commit()
        db.refresh(owner)
        db.refresh(other_user)

        video = models.Video(
            title="Owner's Video",
            user_id=owner.id,
            status="pending",
            original_file_path="/uploads/test.mp4",
            processed_file_path="/processed/test.mp4",
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        token = create_access_token(data={"sub": str(other_user.id)})

        response = client.delete(
            f"/api/videos/{video.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_video_not_found(self, client: TestClient, db):
        """Test deleting non-existent video"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        import uuid

        fake_id = str(uuid.uuid4())

        response = client.delete(
            f"/api/videos/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("app.api.routes.videos.storage")
    def test_delete_video_with_processed_file(self, mock_storage, client: TestClient, db):
        """Test deleting video with processed file that exists"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan_proc@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        video = models.Video(
            title="Processed Video",
            user_id=user.id,
            status="completed",
            original_file_path="/uploads/test.mp4",
            processed_file_path="/processed/test.mp4",
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        # Mock both files can be deleted
        mock_storage.delete_file.return_value = True

        token = create_access_token(data={"sub": str(user.id)})

        response = client.delete(
            f"/api/videos/{video.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        # Verify both files were attempted to be removed
        assert mock_storage.delete_file.call_count == 2

    def test_delete_video_with_votes(self, client: TestClient, db):
        """Test deleting video that has votes"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan_votes@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        video = models.Video(
            title="Voted Video",
            user_id=user.id,
            status="completed",
            is_published=True,
            original_file_path="/uploads/test.mp4",
            processed_file_path="/processed/test.mp4",
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        # Add a vote to the video
        vote = models.Vote(user_id=user.id, video_id=video.id)
        db.add(vote)
        db.commit()

        token = create_access_token(data={"sub": str(user.id)})

        response = client.delete(
            f"/api/videos/{video.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "vote" in response.json()["detail"].lower()

    @patch("app.api.routes.videos.storage")
    def test_delete_video_file_removal_error(self, mock_storage, client: TestClient, db):
        """Test deleting video when file removal fails"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan_remove_error@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        video = models.Video(
            title="Video with File Error",
            user_id=user.id,
            status="completed",
            original_file_path="/uploads/test.mp4",
            processed_file_path="/processed/test.mp4",
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        # Mock file removal returns False (simulating failure)
        mock_storage.delete_file.return_value = False

        token = create_access_token(data={"sub": str(user.id)})

        response = client.delete(
            f"/api/videos/{video.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should still succeed even if file removal fails
        assert response.status_code == status.HTTP_200_OK
        # Verify delete was attempted
        assert mock_storage.delete_file.call_count >= 1


class TestDeleteVideoFile:
    """Tests for _delete_video_file helper function"""

    @patch("app.api.routes.videos.storage")
    def test_delete_video_file_with_empty_path(self, mock_storage):
        """Test _delete_video_file with empty file path"""
        from app.api.routes.videos import _delete_video_file

        # Test with None
        deleted, not_found = _delete_video_file(None, "original")
        assert deleted is False
        assert not_found is True
        mock_storage.delete_file.assert_not_called()

        # Test with empty string
        deleted, not_found = _delete_video_file("", "processed")
        assert deleted is False
        assert not_found is True
        mock_storage.delete_file.assert_not_called()

    @patch("app.api.routes.videos.storage")
    def test_delete_video_file_with_exception(self, mock_storage):
        """Test _delete_video_file handles exceptions gracefully"""
        from app.api.routes.videos import _delete_video_file

        # Mock storage to raise exception
        mock_storage.delete_file.side_effect = Exception("Storage error")

        deleted, not_found = _delete_video_file("/path/to/file.mp4", "original")

        assert deleted is False
        assert not_found is False
        mock_storage.delete_file.assert_called_once_with("/path/to/file.mp4")


class TestPresignedURLs:
    """Tests for S3 presigned URL generation"""

    @patch("app.api.routes.videos.settings")
    @patch("app.api.routes.videos.storage")
    def test_list_videos_with_s3_presigned_urls(self, mock_storage, mock_settings, client: TestClient, db):
        """Test list_user_videos generates presigned URLs for S3"""
        mock_settings.STORAGE_BACKEND = "s3"
        mock_storage.get_presigned_url.return_value = "https://s3.amazonaws.com/presigned-url"

        # Create user
        user = models.User(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password="password",
            city="City",
            country="Country",
        )
        db.add(user)
        db.commit()

        # Create processed video
        video = models.Video(
            user_id=user.id,
            title="Test Video",
            original_file_path="uploads/test.mp4",
            processed_file_path="processed/test.mp4",
            status="processed",
        )
        db.add(video)
        db.commit()

        token = create_access_token(data={"sub": str(user.id)})

        response = client.get(
            "/api/videos/",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        videos = response.json()
        assert len(videos) == 1
        assert videos[0]["processed_url"] == "https://s3.amazonaws.com/presigned-url"
        mock_storage.get_presigned_url.assert_called_once()

    @patch("app.api.routes.videos.settings")
    @patch("app.api.routes.videos.storage")
    def test_list_videos_s3_presigned_url_error(self, mock_storage, mock_settings, client: TestClient, db):
        """Test list_user_videos handles presigned URL generation errors"""
        mock_settings.STORAGE_BACKEND = "s3"
        mock_storage.get_presigned_url.side_effect = Exception("S3 Error")

        # Create user
        user = models.User(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password="password",
            city="City",
            country="Country",
        )
        db.add(user)
        db.commit()

        # Create processed video
        video = models.Video(
            user_id=user.id,
            title="Test Video",
            original_file_path="uploads/test.mp4",
            processed_file_path="processed/test.mp4",
            status="processed",
        )
        db.add(video)
        db.commit()

        token = create_access_token(data={"sub": str(user.id)})

        response = client.get(
            "/api/videos/",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        videos = response.json()
        assert len(videos) == 1
        assert videos[0]["processed_url"] is None

    @patch("app.api.routes.videos.settings")
    def test_list_videos_with_local_storage(self, mock_settings, client: TestClient, db):
        """Test list_user_videos uses regular URLs for local storage"""
        mock_settings.STORAGE_BACKEND = "local"

        # Create user
        user = models.User(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password="password",
            city="City",
            country="Country",
        )
        db.add(user)
        db.commit()

        # Create processed video
        video = models.Video(
            user_id=user.id,
            title="Test Video",
            original_file_path="uploads/test.mp4",
            processed_file_path="processed/test.mp4",
            status="processed",
        )
        db.add(video)
        db.commit()

        token = create_access_token(data={"sub": str(user.id)})

        response = client.get(
            "/api/videos/",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        videos = response.json()
        assert len(videos) == 1
        assert f"https://anb.com/videos/processed/{video.id}.mp4" in videos[0]["processed_url"]

    @patch("app.api.routes.videos.settings")
    @patch("app.api.routes.videos.storage")
    def test_get_video_detail_with_s3_presigned_urls(self, mock_storage, mock_settings, client: TestClient, db):
        """Test get_video_detail generates presigned URLs for S3"""
        mock_settings.STORAGE_BACKEND = "s3"
        mock_storage.get_presigned_url.side_effect = [
            "https://s3.amazonaws.com/original-presigned-url",
            "https://s3.amazonaws.com/processed-presigned-url"
        ]

        # Create user
        user = models.User(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password="password",
            city="City",
            country="Country",
        )
        db.add(user)
        db.commit()

        # Create processed video
        video = models.Video(
            user_id=user.id,
            title="Test Video",
            original_file_path="uploads/test.mp4",
            processed_file_path="processed/test.mp4",
            status="processed",
        )
        db.add(video)
        db.commit()

        token = create_access_token(data={"sub": str(user.id)})

        response = client.get(
            f"/api/videos/{video.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        video_data = response.json()
        assert video_data["original_url"] == "https://s3.amazonaws.com/original-presigned-url"
        assert video_data["processed_url"] == "https://s3.amazonaws.com/processed-presigned-url"
        assert mock_storage.get_presigned_url.call_count == 2

    @patch("app.api.routes.videos.settings")
    @patch("app.api.routes.videos.storage")
    def test_get_video_detail_s3_presigned_url_error(self, mock_storage, mock_settings, client: TestClient, db):
        """Test get_video_detail handles presigned URL generation errors"""
        mock_settings.STORAGE_BACKEND = "s3"
        mock_storage.get_presigned_url.side_effect = Exception("S3 Error")

        # Create user
        user = models.User(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password="password",
            city="City",
            country="Country",
        )
        db.add(user)
        db.commit()

        # Create processed video
        video = models.Video(
            user_id=user.id,
            title="Test Video",
            original_file_path="uploads/test.mp4",
            processed_file_path="processed/test.mp4",
            status="processed",
        )
        db.add(video)
        db.commit()

        token = create_access_token(data={"sub": str(user.id)})

        response = client.get(
            f"/api/videos/{video.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        video_data = response.json()
        assert video_data["original_url"] is None
        assert video_data["processed_url"] is None

    @patch("app.api.routes.videos.settings")
    def test_get_video_detail_with_local_storage(self, mock_settings, client: TestClient, db):
        """Test get_video_detail uses regular URLs for local storage"""
        mock_settings.STORAGE_BACKEND = "local"

        # Create user
        user = models.User(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password="password",
            city="City",
            country="Country",
        )
        db.add(user)
        db.commit()

        # Create processed video
        video = models.Video(
            user_id=user.id,
            title="Test Video",
            original_file_path="uploads/test.mp4",
            processed_file_path="processed/test.mp4",
            status="processed",
        )
        db.add(video)
        db.commit()

        token = create_access_token(data={"sub": str(user.id)})

        response = client.get(
            f"/api/videos/{video.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        video_data = response.json()
        assert f"https://anb.com/uploads/{video.id}.mp4" in video_data["original_url"]
        assert f"https://anb.com/processed/{video.id}.mp4" in video_data["processed_url"]
