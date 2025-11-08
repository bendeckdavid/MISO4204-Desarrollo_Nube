"""Tests for video management endpoints"""
import io
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status
from fastapi.testclient import TestClient

from app.db import models
from app.core.security import create_access_token


class TestVideoUpload:
    """Tests for video upload endpoint"""

    @patch("app.api.routes.videos.process_video")
    @patch("app.api.routes.videos.os.path.exists")
    @patch("app.api.routes.videos.os.path.getsize")
    @patch("app.api.routes.videos.os.makedirs")
    @patch("app.api.routes.videos.aiofiles.open", create=True)
    def test_upload_video_success(
        self,
        mock_aiofiles_open,
        mock_makedirs,
        mock_getsize,
        mock_exists,
        mock_process_video,
        client: TestClient,
        db,
    ):
        """Test successful video upload"""
        # Mock file operations
        mock_exists.return_value = True
        mock_getsize.return_value = 1024
        mock_file = MagicMock()
        mock_file.write = AsyncMock()
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file
        mock_aiofiles_open.return_value.__aexit__.return_value = None

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
