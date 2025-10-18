"""Video schemas"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class VideoUploadRequest(BaseModel):
    """Schema for video upload request"""

    test: str


class VideoUploadResponse(BaseModel):
    """Schema for video response"""

    id: str
    user_id: str


class VideoDetailResponse(BaseModel):
    """Full video information"""

    video_id: str
    title: str
    status: str
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    processed_url: Optional[str] = None
