"""Tests for security module"""
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import get_current_user_optional
from app.db import models


class TestGetCurrentUserOptional:
    """Tests for get_current_user_optional function"""

    def test_get_current_user_optional_no_credentials(self, db):
        """Test with no credentials provided"""
        result = get_current_user_optional(credentials=None, db=db)
        assert result is None

    def test_get_current_user_optional_invalid_token(self, db):
        """Test with invalid JWT token"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid.token.here"
        )

        result = get_current_user_optional(credentials=credentials, db=db)
        assert result is None

    def test_get_current_user_optional_token_missing_sub(self, db):
        """Test with token that doesn't have 'sub' claim"""
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        from app.core.config import settings
        from app.core.security import ALGORITHM

        # Create token without 'sub' claim
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        token_data = {"exp": expire, "other": "data"}
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=ALGORITHM)

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = get_current_user_optional(credentials=credentials, db=db)
        assert result is None

    def test_get_current_user_optional_nonexistent_user(self, db):
        """Test with valid token but user doesn't exist"""
        import uuid

        from app.core.security import create_access_token

        fake_user_id = str(uuid.uuid4())
        token = create_access_token(data={"sub": fake_user_id})

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = get_current_user_optional(credentials=credentials, db=db)
        assert result is None

    def test_get_current_user_optional_success(self, db):
        """Test with valid token and existing user"""
        from app.core.security import create_access_token

        # Create a test user
        user = models.User(
            first_name="Test",
            last_name="User",
            email="optional_test@example.com",
            password="hashed_password",
            city="Bogotá",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create valid token for this user
        token = create_access_token(data={"sub": str(user.id)})

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = get_current_user_optional(credentials=credentials, db=db)
        assert result is not None
        assert result.id == user.id
        assert result.email == user.email

    def test_get_current_user_optional_generic_exception(self, db):
        """Test handling of generic exceptions"""
        from app.core.security import create_access_token

        # Create a test user
        user = models.User(
            first_name="Test",
            last_name="User",
            email="exception_test@example.com",
            password="hashed_password",
            city="Cali",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Mock db.query to raise an exception
        original_query = db.query

        def mock_query(*args, **kwargs):
            raise Exception("Database error")

        db.query = mock_query

        try:
            result = get_current_user_optional(credentials=credentials, db=db)
            assert result is None
        finally:
            # Restore original query
            db.query = original_query
