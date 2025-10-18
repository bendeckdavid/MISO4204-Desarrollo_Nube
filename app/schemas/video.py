"""Video schemas"""

from pydantic import BaseModel


class VideoUploadRequest(BaseModel):
    """Schema for video upload request"""

    test: str

class VideoResponse(BaseModel):
    """Schema for video response"""

    id: str
    user_id: str
