"""Video schemas"""

from pydantic import BaseModel
from typing import Optional


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
