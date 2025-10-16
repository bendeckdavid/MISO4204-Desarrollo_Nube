"""Security utilities: API Key validation"""

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def verify_api_key(
    x_api_key: str = Header(..., description="API Key for authentication")
) -> str:
    """Validate API Key from header"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key not provided",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key
