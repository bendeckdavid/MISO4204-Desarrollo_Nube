"""Tests for database models"""
from app.db import models


class TestUserModel:
    """Tests for User model"""

    def test_user_repr(self, db):
        """Test User __repr__ method"""
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan@test.com",
            password="password123",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        repr_str = repr(user)
        assert "User" in repr_str
        assert user.email in repr_str


class TestVideoModel:
    """Tests for Video model"""

    def test_video_repr(self, db):
        """Test Video __repr__ method"""
        user = models.User(
            first_name="Test",
            last_name="User",
            email="test@test.com",
            password="password123",
            city="Bogotá",
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

        repr_str = repr(video)
        assert "Video" in repr_str
        assert video.title in repr_str

    def test_video_vote_count(self, db):
        """Test Video vote_count property"""
        user = models.User(
            first_name="Test",
            last_name="User",
            email="test_vote@test.com",
            password="password123",
            city="Cali",
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
            is_published=True,
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        # Initially no votes
        assert video.vote_count == 0

        # Add a vote
        vote = models.Vote(user_id=user.id, video_id=video.id)
        db.add(vote)
        db.commit()

        # Refresh to get updated count
        db.refresh(video)
        assert video.vote_count == 1


class TestVoteModel:
    """Tests for Vote model"""

    def test_vote_repr(self, db):
        """Test Vote __repr__ method"""
        user = models.User(
            first_name="Voter",
            last_name="User",
            email="voter@test.com",
            password="password123",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        video = models.Video(
            title="Video to Vote",
            user_id=user.id,
            status="completed",
            original_file_path="/uploads/test.mp4",
            processed_file_path="/processed/test.mp4",
            is_published=True,
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        vote = models.Vote(user_id=user.id, video_id=video.id)
        db.add(vote)
        db.commit()
        db.refresh(vote)

        repr_str = repr(vote)
        assert "Vote" in repr_str
        assert str(user.id) in repr_str
        assert str(video.id) in repr_str
