"""Video endpoints for ANB Rising Stars Showcase"""

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.config import settings
from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db
from app.schemas.video import VideoUploadResponse, VideoUploadRequest,VideoDetailResponse
from app.worker.videos import process_video
import os

router = APIRouter()


@router.post("/upload", response_model=VideoUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_video(
    data: VideoUploadRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allow users to upload videos

    Starts the async processing of the video
    """

    # Validate video file existence
    if not data.file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded")
    # Validate the file size is not larger than the maximum allowed size
    if len(data.file) > settings.MAX_VIDEO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File size exceeds limit"
        )

    new_video_id = models.generate_uuid()
    video_file_path = f"/videos/uploads/{new_video_id}.mp4"
    processed_file_path = f"/videos/processed/{new_video_id}.mp4"

    # Create database record
    video = models.Video(
        id=new_video_id,
        user_id=current_user.id,
        title=data.title,
        original_file_path=video_file_path,
        processed_file_path=processed_file_path,
    )

    db.add(video)
    db.commit()
    db.refresh(video)

    # Create the /videos/uploads/ directory if it doesn't exist
    os.makedirs(os.path.dirname(video_file_path), exist_ok=True)

    # Save the uploaded file to disk
    with open(video_file_path, "wb") as f:
        f.write(data.file)

    # Dispatch Celery task to process the video
    process_video(new_video_id)

    return {
        "video_id": new_video_id,
        "user_id": str(current_user.id),
    }


@router.get("/", response_model=List[VideoDetailResponse], status_code=status.HTTP_200_OK)
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
