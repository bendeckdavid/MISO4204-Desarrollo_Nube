"""Database models"""

import bcrypt
from sqlalchemy import Column, String
from sqlalchemy.ext.hybrid import hybrid_property

from app.db.base import Base


class User(Base):
    """User model for ANB Rising Stars players"""

    __tablename__ = "users"

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    _password = Column("password", String(255), nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)

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


class Task(Base):
    """Task model - TEMPLATE (to be replaced with Video model)"""

    __tablename__ = "tasks"

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    def __repr__(self):
        return f"<Task {self.name}>"
