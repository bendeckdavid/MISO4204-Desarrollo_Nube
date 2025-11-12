"""Tests for authentication endpoints"""
import uuid

from fastapi import status
from fastapi.testclient import TestClient

from app.db import models


class TestSignup:
    """Tests for the signup endpoint"""

    def test_signup_success(self, client: TestClient, db):
        """Test successful user registration"""
        response = client.post(
            "/api/auth/signup",
            json={
                "first_name": "Juan",
                "last_name": "Pérez",
                "email": "juan.perez@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
                "city": "Medellín",
                "country": "Colombia",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "juan.perez@example.com"
        assert data["first_name"] == "Juan"
        assert data["last_name"] == "Pérez"
        assert data["city"] == "Medellín"
        assert data["country"] == "Colombia"
        assert "id" in data
        # Verify ID is a valid UUID string
        assert uuid.UUID(data["id"])
        assert "password" not in data
        assert "password_hash" not in data

    def test_signup_duplicate_email(self, client: TestClient, db):
        """Test signup with duplicate email returns 400"""
        # Create first user
        user = models.User(
            first_name="Existing",
            last_name="User",
            email="existing@example.com",
            password="password123",
            city="Bogotá",
            country="Colombia",
        )
        db.add(user)
        db.commit()

        # Try to create user with same email
        response = client.post(
            "/api/auth/signup",
            json={
                "first_name": "New",
                "last_name": "User",
                "email": "existing@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
                "city": "Cali",
                "country": "Colombia",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "registrado" in response.json()["detail"].lower()

    def test_signup_password_mismatch(self, client: TestClient, db):
        """Test signup with mismatched passwords returns validation error"""
        response = client.post(
            "/api/auth/signup",
            json={
                "first_name": "Juan",
                "last_name": "Pérez",
                "email": "juan.perez@example.com",
                "password1": "SecurePass123!",
                "password2": "DifferentPass456!",
                "city": "Medellín",
                "country": "Colombia",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Las contraseñas no coinciden" in str(response.json())

    def test_signup_missing_fields(self, client: TestClient, db):
        """Test signup with missing required fields"""
        response = client.post(
            "/api/auth/signup",
            json={
                "email": "incomplete@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_invalid_email(self, client: TestClient, db):
        """Test signup with invalid email format"""
        response = client.post(
            "/api/auth/signup",
            json={
                "first_name": "Juan",
                "last_name": "Pérez",
                "email": "not-an-email",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
                "city": "Medellín",
                "country": "Colombia",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLogin:
    """Tests for the login endpoint"""

    def test_login_success(self, client: TestClient, db):
        """Test successful login returns JWT token"""
        # Create a user
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan.perez@example.com",
            password="SecurePass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()

        # Login
        response = client.post(
            "/api/auth/login",
            json={
                "email": "juan.perez@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert "expires_in" in data
        assert data["expires_in"] > 0

    def test_login_wrong_password(self, client: TestClient, db):
        """Test login with wrong password returns 401"""
        # Create a user
        user = models.User(
            first_name="Juan",
            last_name="Pérez",
            email="juan.perez@example.com",
            password="CorrectPass123!",
            city="Medellín",
            country="Colombia",
        )
        db.add(user)
        db.commit()

        # Try to login with wrong password
        response = client.post(
            "/api/auth/login",
            json={
                "email": "juan.perez@example.com",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrectos" in response.json()["detail"]

    def test_login_nonexistent_email(self, client: TestClient, db):
        """Test login with non-existent email returns 401"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrectos" in response.json()["detail"]

    def test_login_missing_fields(self, client: TestClient, db):
        """Test login with missing fields returns validation error"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "juan.perez@example.com",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestTokenFunctions:
    """Tests for JWT token creation and validation"""

    def test_create_token_with_custom_expiration(self, client: TestClient, db):
        """Test creating token with custom expiration"""
        from datetime import timedelta

        from app.core.security import create_access_token

        user = models.User(
            first_name="Test",
            last_name="User",
            email="token@test.com",
            password="SecurePass123!",
            city="Bogotá",
            country="Colombia",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create token with custom 1-minute expiration
        token = create_access_token(data={"sub": str(user.id)}, expires_delta=timedelta(minutes=1))

        # Token should work immediately
        response = client.get(
            "/api/videos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_token_missing_sub(self, client: TestClient, db):
        """Test token without 'sub' claim"""
        from app.core.security import create_access_token

        # Create token without 'sub' field
        token = create_access_token(data={"user": "invalid"})

        response = client.get(
            "/api/videos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_with_nonexistent_user(self, client: TestClient, db):
        """Test token with valid format but non-existent user"""
        import uuid

        from app.core.security import create_access_token

        # Create token with non-existent user ID
        fake_user_id = str(uuid.uuid4())
        token = create_access_token(data={"sub": fake_user_id})

        response = client.get(
            "/api/videos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found" in response.json()["detail"]


class TestProtectedEndpoint:
    """Tests for protected endpoints with JWT authentication"""

    def test_upload_without_token(self, client: TestClient, db):
        """Test accessing protected endpoint without token returns 403"""
        response = client.post(
            "/api/videos/upload",
            json={
                "title": "My Video",
                "file": "AAAAHGZ0eXBtcDR2AAAAAG1wNHZtcDQyaXNvbQAAABhiZWFtAQAAAAEAAAAAAAAAAgA",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_with_invalid_token(self, client: TestClient, db):
        """Test accessing protected endpoint with invalid token returns 401"""
        response = client.post(
            "/api/videos/upload",
            json={
                "title": "My Video",
                "file": "AAAAHGZ0eXBtcDR2AAAAAG1wNHZtcDQyaXNvbQAAABhiZWFtAQAAAAEAAAAAAAAAAgA",
            },
            headers={"Authorization": "Bearer invalid-token-12345"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_with_malformed_header(self, client: TestClient, db):
        """Test accessing protected endpoint with malformed auth header"""
        response = client.post(
            "/api/videos/upload",
            json={
                "title": "My Video",
                "file": "AAAAHGZ0eXBtcDR2AAAAAG1wNHZtcDQyaXNvbQAAABhiZWFtAQAAAAEAAAAAAAAAAgA",
            },
            headers={"Authorization": "InvalidFormat token123"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
