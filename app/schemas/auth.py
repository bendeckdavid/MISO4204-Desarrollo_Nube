"""Authentication schemas"""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    """Schema for user registration"""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password1: str = Field(..., min_length=8, description="Password (min 8 characters)")
    password2: str = Field(..., min_length=8, description="Password confirmation")
    city: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=1, max_length=100)

    @field_validator("password2")
    def passwords_match(cls, v, info):
        """Validate that both passwords match"""
        if "password1" in info.data and v != info.data["password1"]:
            raise ValueError("Las contraseñas no coinciden")
        return v


class LoginRequest(BaseModel):
    """Schema for user login"""

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema for JWT token response"""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600


class UserResponse(BaseModel):
    """Schema for user data in responses"""

    id: UUID
    first_name: str
    last_name: str
    email: str
    city: str
    country: str

    class Config:
        from_attributes = True
        json_encoders = {UUID: str}
