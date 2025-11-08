"""Tests for public endpoints (videos, voting, ranking)"""
from fastapi import status
from fastapi.testclient import TestClient

from app.db import models
from app.core.security import create_access_token


class TestListPublicVideos:
    """Tests for listing public videos"""

    def test_list_public_videos_success(self, client: TestClient, db):
        """Test successful retrieval of public videos"""
        # Create users and videos
        user1 = models.User(
            first_name="Player1",
            last_name="One",
            email="player1@example.com",
            password="SecurePass123!",
            city="Bogotá",
            country="Colombia",
        )
        user2 = models.User(
            first_name="Player2",
            last_name="Two",
            email="player2@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)

        # Create processed public videos
        video1 = models.Video(
            title="Public Video 1",
            user_id=user1.id,
            status="completed",
            original_file_path="/uploads/video1.mp4",
            processed_file_path="/processed/video1.mp4",
            is_published=True,
        )
        video2 = models.Video(
            title="Public Video 2",
            user_id=user2.id,
            status="completed",
            original_file_path="/uploads/video2.mp4",
            processed_file_path="/processed/video2.mp4",
            is_published=True,
        )
        # Private video should not appear
        video3 = models.Video(
            title="Private Video",
            user_id=user1.id,
            status="completed",
            original_file_path="/uploads/video3.mp4",
            processed_file_path="/processed/video3.mp4",
            is_published=False,
        )
        db.add_all([video1, video2, video3])
        db.commit()

        response = client.get("/api/public/videos")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        # Should only return public videos
        assert len(data) >= 2
        titles = [v["title"] for v in data]
        assert "Public Video 1" in titles
        assert "Public Video 2" in titles
        assert "Private Video" not in titles

    def test_list_public_videos_empty(self, client: TestClient, db):
        """Test listing public videos when none exist"""
        response = client.get("/api/public/videos")

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)


class TestVoteVideo:
    """Tests for voting on videos"""

    def test_vote_video_success(self, client: TestClient, db):
        """Test successful vote on a video"""
        # Create user and video
        owner = models.User(
            first_name="Owner",
            last_name="User",
            email="owner@example.com",
            password="SecurePass123!",
            city="Bogotá",
            country="Colombia",
        )
        voter = models.User(
            first_name="Voter",
            last_name="User",
            email="voter@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add_all([owner, voter])
        db.commit()
        db.refresh(owner)
        db.refresh(voter)

        video = models.Video(
            title="Video to Vote",
            user_id=owner.id,
            status="completed",
            original_file_path="/uploads/video.mp4",
            processed_file_path="/processed/video.mp4",
            is_published=True,
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        token = create_access_token(data={"sub": str(voter.id)})

        response = client.post(
            f"/api/public/videos/{video.id}/vote",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "voto" in data["message"].lower() or "registrado" in data["message"].lower()

    def test_vote_video_without_auth(self, client: TestClient, db):
        """Test voting without authentication"""
        user = models.User(
            first_name="Owner",
            last_name="User",
            email="owner@example.com",
            password="SecurePass123!",
            city="Bogotá",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        video = models.Video(
            title="Video to Vote",
            user_id=user.id,
            status="completed",
            original_file_path="/uploads/video.mp4",
            processed_file_path="/processed/video.mp4",
            is_published=True,
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        response = client.post(f"/api/public/videos/{video.id}/vote")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_vote_video_duplicate(self, client: TestClient, db):
        """Test voting twice on the same video"""
        owner = models.User(
            first_name="Owner",
            last_name="User",
            email="owner@example.com",
            password="SecurePass123!",
            city="Bogotá",
            country="Colombia",
        )
        voter = models.User(
            first_name="Voter",
            last_name="User",
            email="voter@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add_all([owner, voter])
        db.commit()
        db.refresh(owner)
        db.refresh(voter)

        video = models.Video(
            title="Video to Vote",
            user_id=owner.id,
            status="completed",
            original_file_path="/uploads/video.mp4",
            processed_file_path="/processed/video.mp4",
            is_published=True,
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        # Create existing vote
        vote = models.Vote(user_id=voter.id, video_id=video.id)
        db.add(vote)
        db.commit()

        token = create_access_token(data={"sub": str(voter.id)})

        response = client.post(
            f"/api/public/videos/{video.id}/vote",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "votado" in response.json()["detail"].lower()

    def test_vote_video_not_found(self, client: TestClient, db):
        """Test voting on non-existent video"""
        user = models.User(
            first_name="Voter",
            last_name="User",
            email="voter@example.com",
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

        response = client.post(
            f"/api/public/videos/{fake_id}/vote",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_vote_video_not_processed(self, client: TestClient, db):
        """Test voting on a video that is not yet processed"""
        owner = models.User(
            first_name="Owner",
            last_name="User",
            email="owner_pending@example.com",
            password="SecurePass123!",
            city="Bogotá",
            country="Colombia",
        )
        voter = models.User(
            first_name="Voter",
            last_name="User",
            email="voter_pending@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add_all([owner, voter])
        db.commit()
        db.refresh(owner)
        db.refresh(voter)

        # Create video with pending status
        video = models.Video(
            title="Pending Video",
            user_id=owner.id,
            status="pending",
            original_file_path="/uploads/video.mp4",
            processed_file_path="/processed/video.mp4",
            is_published=True,
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        token = create_access_token(data={"sub": str(voter.id)})

        response = client.post(
            f"/api/public/videos/{video.id}/vote",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "disponible" in response.json()["detail"].lower()


class TestRanking:
    """Tests for ranking endpoint"""

    def test_get_ranking_success(self, client: TestClient, db):
        """Test successful retrieval of ranking"""
        # Create users
        user1 = models.User(
            first_name="Player1",
            last_name="One",
            email="player1@example.com",
            password="SecurePass123!",
            city="Bogotá",
            country="Colombia",
        )
        user2 = models.User(
            first_name="Player2",
            last_name="Two",
            email="player2@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)

        # Create videos
        video1 = models.Video(
            title="Video 1",
            user_id=user1.id,
            status="completed",
            original_file_path="/uploads/video1.mp4",
            processed_file_path="/processed/video1.mp4",
            is_published=True,
        )
        video2 = models.Video(
            title="Video 2",
            user_id=user2.id,
            status="completed",
            original_file_path="/uploads/video2.mp4",
            processed_file_path="/processed/video2.mp4",
            is_published=True,
        )
        db.add_all([video1, video2])
        db.commit()
        db.refresh(video1)
        db.refresh(video2)

        # Create votes (video1 has more votes)
        voter1 = models.User(
            first_name="Voter1",
            last_name="Test",
            email="voter1@example.com",
            password="SecurePass123!",
            city="Cali",
            country="Colombia",
        )
        voter2 = models.User(
            first_name="Voter2",
            last_name="Test",
            email="voter2@example.com",
            password="SecurePass123!",
            city="Cali",
            country="Colombia",
        )
        db.add_all([voter1, voter2])
        db.commit()
        db.refresh(voter1)
        db.refresh(voter2)

        vote1 = models.Vote(user_id=voter1.id, video_id=video1.id)
        vote2 = models.Vote(user_id=voter2.id, video_id=video1.id)
        vote3 = models.Vote(user_id=voter1.id, video_id=video2.id)
        db.add_all([vote1, vote2, vote3])
        db.commit()

        response = client.get("/api/public/rankings")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        assert "rankings" in data
        assert isinstance(data["rankings"], list)
        assert len(data["rankings"]) >= 2

        # Check ranking order (highest votes first)
        if len(data["rankings"]) >= 2:
            assert data["rankings"][0]["votes"] >= data["rankings"][1]["votes"]

    def test_get_ranking_with_city_filter(self, client: TestClient, db):
        """Test ranking with city filter"""
        # Create users from different cities
        user_bogota = models.User(
            first_name="PlayerBogota",
            last_name="One",
            email="bogota@example.com",
            password="SecurePass123!",
            city="Bogotá",
            country="Colombia",
        )
        user_medellin = models.User(
            first_name="PlayerMedellin",
            last_name="Two",
            email="medellin@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add_all([user_bogota, user_medellin])
        db.commit()
        db.refresh(user_bogota)
        db.refresh(user_medellin)

        # Create videos
        video_bogota = models.Video(
            title="Bogota Video",
            user_id=user_bogota.id,
            status="completed",
            original_file_path="/uploads/video1.mp4",
            processed_file_path="/processed/video1.mp4",
            is_published=True,
        )
        video_medellin = models.Video(
            title="Medellin Video",
            user_id=user_medellin.id,
            status="completed",
            original_file_path="/uploads/video2.mp4",
            processed_file_path="/processed/video2.mp4",
            is_published=True,
        )
        db.add_all([video_bogota, video_medellin])
        db.commit()

        response = client.get("/api/public/rankings?city=Bogotá")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        assert "rankings" in data
        # Should only contain Bogotá players
        for player in data["rankings"]:
            if "city" in player:
                assert player["city"] == "Bogotá"

    def test_get_ranking_empty(self, client: TestClient, db):
        """Test ranking when no videos exist"""
        response = client.get("/api/public/rankings")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        assert "rankings" in data
        assert isinstance(data["rankings"], list)
