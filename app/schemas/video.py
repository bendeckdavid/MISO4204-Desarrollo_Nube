"""Video schemas"""

from typing import Optional

from pydantic import BaseModel, Field


class VideoUploadRequest(BaseModel):
    """Schema for video upload request"""

    test: str


class VideoUploadResponse(BaseModel):
    """Schema for video response"""

    video_id: str
    user_id: str


class VideoDetailResponse(BaseModel):
    """Full video information"""

    video_id: str
    title: str
    status: str
    uploaded_at: Optional[str] = None
    processed_at: Optional[str] = None
    original_url: Optional[str] = None
    processed_url: Optional[str] = None
    votes: Optional[int] = 0


class VideoDeleteResponse(BaseModel):
    """Response after deleting a video"""

    message: str = Field(..., example="El video ha sido eliminado exitosamente.")
    video_id: str = Field(..., example="a1b2c3d4")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "El video ha sido eliminado exitosamente.",
                "video_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
