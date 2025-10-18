"""Video endpoints for ANB Rising Stars Showcase"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db
from app.schemas.video import VideoResponse, VideoUploadRequest

router = APIRouter()


@router.post("/upload", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def upload_video(
    data: VideoUploadRequest, # TODO: Change to VideoUploadRequest
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allow users to upload videos
    
    Starts the async processing of the video
    """
    return {
        "id": "example-video-id",
        "user_id": str(current_user.id),
    }
