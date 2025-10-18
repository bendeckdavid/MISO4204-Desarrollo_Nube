"""Video schemas"""

from pydantic import BaseModel


class VideoUploadRequest(BaseModel):
    """Schema for video upload request accept a file and a video title from the current logged in user"""

    title: str
    file: bytes


class VideoUploadResponse(BaseModel):
    """Schema for video upload response"""

    video_id: str
    user_id: str
