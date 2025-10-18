"""Video endpoints for ANB Rising Stars Showcase"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db
from app.schemas.video import VideoResponse, VideoUploadRequest

router = APIRouter()


@router.post("/upload", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def upload_video(
    data: VideoUploadRequest,
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


@router.get("/", response_model=List[VideoResponse], status_code=status.HTTP_200_OK)
def list_user_videos(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    videos = db.query(models.Video).filter(models.Video.user_id == current_user.id).all()

    response = []
    for video in videos:
        video_data = {
            "video_id": str(video.id),
            "title": video.title,
            "status": video.status,
            "uploaded_at": video.created_at.isoformat() if hasattr(video, "created_at") else None,
        }

        if video.status == "processed" or video.status == "completed":
            video_data["processed_at"] = (
                video.updated_at.isoformat() if hasattr(video, "updated_at") else None
            )
            video_data["processed_url"] = f"https://anb.com/videos/processed/{video.id}.mp4"

        response.append(video_data)

    return response
