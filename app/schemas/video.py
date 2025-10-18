"""Video schemas"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VideoUploadRequest(BaseModel):
    """Schema for video upload request"""

    test: str


class VideoResponse(BaseModel):
    """Schema for video response"""

    video_id: str
    title: str
    status: str
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    processed_url: Optional[str] = None
