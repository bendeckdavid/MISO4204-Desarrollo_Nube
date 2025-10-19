"""Video endpoints for ANB Rising Stars Showcase"""

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from app.core.config import settings
from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db
from app.schemas.video import VideoUploadResponse, VideoDetailResponse
from app.worker.videos import process_video
import os

router = APIRouter()


@router.post("/upload", response_model=VideoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allow users to upload videos

    Starts the async processing of the video
    """

    # Validate video file existence
    if not file or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded")

    # Validate file type
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a video format"
        )

    # Validate the file size is not larger than the maximum allowed size
    if file.size and file.size > settings.MAX_VIDEO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File size exceeds limit"
        )

    new_video_id = models.generate_uuid()
    # Use app directory which is shared between API and Worker containers
    video_file_path = f"/app/videos/uploads/{new_video_id}.mp4"
    processed_file_path = f"/app/videos/processed/{new_video_id}.mp4"

    # Create database record
    video = models.Video(
        id=new_video_id,
        user_id=current_user.id,
        title=title,
        original_file_path=video_file_path,
        processed_file_path=processed_file_path,
    )

    db.add(video)
    db.commit()
    db.refresh(video)

    # Create the /videos/uploads/ directory if it doesn't exist
    os.makedirs(os.path.dirname(video_file_path), exist_ok=True)
    os.makedirs(os.path.dirname(processed_file_path), exist_ok=True)

    # Save the uploaded file to disk
    try:
        # Reset file pointer to beginning
        file.file.seek(0)
        # Read the entire content into memory (for small-to-medium video files)
        content = file.file.read()

        # Write to disk synchronously
        with open(video_file_path, "wb") as f:
            f.write(content)
        # Verify the saved file
        if os.path.exists(video_file_path):
            file_size = os.path.getsize(video_file_path)
            print(file_size)
        else:
            raise FileNotFoundError("File was not saved properly")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}",
        )

    # Dispatch Celery task to process the video asynchronously
    process_video.apply_async(args=[new_video_id])

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


@router.get("/{video_id}", response_model=VideoDetailResponse, status_code=status.HTTP_200_OK)
def get_video_detail(
    video_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific video.
    Includes URLs for download/preview if available.
    """

    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Validar que el video pertenece al usuario autenticado
    if video.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: this video does not belong to you")

    # Crear la respuesta
    return {
        "video_id": str(video.id),
        "title": video.title,
        "status": video.status,
        "uploaded_at": video.created_at.isoformat() if hasattr(video, "created_at") else None,
        "processed_at": video.updated_at.isoformat() if hasattr(video, "updated_at") else None,
        "original_url": f"https://anb.com/uploads/{video.id}.mp4",
        "processed_url": f"https://anb.com/processed/{video.id}.mp4"
        if video.status == "processed"
        else None,
        "votes": getattr(video, "votes", 0),
    }
