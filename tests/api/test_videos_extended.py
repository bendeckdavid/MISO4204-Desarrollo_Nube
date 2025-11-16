"""Extended tests for video routes to achieve 100% coverage"""
import io
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db import models


class TestVideoUploadExtended:
    """Extended tests for video upload endpoint"""

    @patch("app.api.routes.videos.sqs_service")
    @patch("app.api.routes.videos.storage")
    def test_upload_video_sqs_failure(self, mock_storage, mock_sqs_service, client: TestClient, db):
        """Test video upload when SQS fails but upload succeeds"""
        # Mock storage operations
        mock_storage.upload_file.return_value = "uploads/test_video.mp4"
        mock_storage.file_exists.return_value = True

        # Mock SQS to raise exception
        mock_sqs_service.send_message.side_effect = Exception("SQS connection failed")

        # Create and login user
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan_sqs@example.com",
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

        # Upload should succeed even if SQS fails
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "video_id" in data or "id" in data

    @patch("app.api.routes.videos.sqs_service")
    @patch("app.api.routes.videos.storage")
    def test_upload_video_no_file_object(
        self, mock_storage, mock_sqs_service, client: TestClient, db
    ):
        """Test video upload with null file"""
        # Create and login user
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan_null@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        # Don't send file at all
        response = client.post(
            "/api/videos/upload",
            data={"title": "Test"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should fail with 422 (missing required field)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
