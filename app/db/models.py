"""Database models"""

import uuid
from datetime import datetime

import bcrypt
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from app.db.base import Base


def generate_uuid() -> str:
    """Generate a new UUID string"""
    return str(uuid.uuid4())


class User(Base):
    """User model for ANB Rising Stars players"""

    __tablename__ = "users"

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    _password = Column("password", String(255), nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)

    videos = relationship("Video", back_populates="user")
    votes = relationship("Vote", back_populates="user", cascade="all, delete-orphan")

    @hybrid_property
    def password(self):
        """Password property - write-only"""
        return self._password

    @password.setter  # type: ignore
    def password(self, plaintext_password: str):
        """
        Hash password using bcrypt when setting it.

        :param plaintext_password: User's plaintext password
        """
        self._password = bcrypt.hashpw(plaintext_password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

    def verify_password(self, plaintext_password: str) -> bool:
        """
        Verify a plaintext password against the stored hash.

        :param plaintext_password: Password to verify
        :return: True if password matches, False otherwise
        """
        return bcrypt.checkpw(plaintext_password.encode("utf-8"), self._password.encode("utf-8"))

    def __repr__(self):
        return f"<User {self.email}>"


class Video(Base):
    """Video model"""

    __tablename__ = "videos"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="videos")
    votes = relationship("Vote", back_populates="video", cascade="all, delete-orphan")

    title = Column(String, nullable=False)
    original_file_path = Column(String, nullable=False)
    processed_file_path = Column(String, nullable=False)
    # pending, processing, completed, failed
    status = Column(String, nullable=False, default="pending")
    is_published = Column(Boolean, nullable=False, default=False)

    @hybrid_property
    def vote_count(self):
        """Get the number of votes for this video"""
        return len(self.votes) if self.votes else 0

    def __repr__(self):
        return f"<Video {self.title}>"


class Vote(Base):
    """Vote model - tracks user votes for videos"""

    __tablename__ = "votes"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False, index=True)
    voted_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="votes")
    video = relationship("Video", back_populates="votes")

    # Unique constraint: one vote per user per video
    __table_args__ = (UniqueConstraint("user_id", "video_id", name="uq_user_video_vote"),)

    def __repr__(self):
        return f"<Vote user={self.user_id} video={self.video_id}>"
