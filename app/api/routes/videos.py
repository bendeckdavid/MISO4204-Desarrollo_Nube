"""Video endpoints for ANB Rising Stars Showcase"""

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from app.core.config import settings
from app.core.security import get_current_user
from app.core.storage import storage
from app.db import models
from app.db.database import get_db
from app.schemas.video import VideoUploadResponse, VideoDetailResponse, VideoDeleteResponse
from app.worker.videos import process_video

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

    # Build storage paths based on backend (S3 or local)
    if settings.STORAGE_BACKEND == "s3":
        video_file_path = f"{settings.S3_UPLOAD_PREFIX}{new_video_id}.mp4"
        processed_file_path = f"{settings.S3_PROCESSED_PREFIX}{new_video_id}.mp4"
    else:
        video_file_path = f"{settings.UPLOAD_BASE_DIR}/{new_video_id}.mp4"
        processed_file_path = f"{settings.PROCESSED_BASE_DIR}/{new_video_id}.mp4"

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

    # Upload file using storage backend (local or S3)
    try:
        # Reset file pointer to beginning
        file.file.seek(0)
        # Read the entire content into memory
        content = file.file.read()

        # Upload using storage backend
        storage.upload_file(content, video_file_path)

        # Verify upload
        if not storage.file_exists(video_file_path):
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
            "votes": video.vote_count,
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
        "votes": video.vote_count,
    }


def _delete_video_file(file_path: str, file_type: str) -> tuple[bool, bool]:
    """
    Helper function to delete a single video file.

    Returns:
        tuple: (deleted, not_found) - True if file was deleted, True if file was not found
    """
    if not file_path:
        return False, True

    try:
        if storage.delete_file(file_path):
            return True, False
        return False, True
    except Exception as e:
        print(f"Error deleting {file_type} file: {e}")
        return False, False


@router.delete("/{video_id}", response_model=VideoDeleteResponse, status_code=status.HTTP_200_OK)
async def delete_video(
    video_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a video uploaded by the authenticated user.

    Rules:
    - Only the video owner can delete it
    - Video cannot be deleted if it's published for voting
    - Video cannot be deleted if it has votes
    - Both original and processed files are deleted from disk

    Returns:
        200: Video deleted successfully
        400: Video cannot be deleted (published or has votes)
        401: User not authenticated
        403: User is not the video owner
        404: Video not found
    """

    # 1. Check if video exists
    video = db.query(models.Video).filter(models.Video.id == video_id).first()

    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    # 2. Check if user is the owner
    if video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: you don't have permission to delete this video",
        )

    # 4. Check if video has votes
    vote_count = db.query(models.Vote).filter(models.Vote.video_id == video_id).count()
    if vote_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete video: it has {vote_count} vote(s)",
        )

    # 5. Delete files from storage (local or S3)
    files_deleted = []
    files_not_found = []

    # Delete original file
    deleted, not_found = _delete_video_file(video.original_file_path, "original")
    if deleted:
        files_deleted.append("original")
    if not_found:
        files_not_found.append("original")

    # Delete processed file
    deleted, not_found = _delete_video_file(video.processed_file_path, "processed")
    if deleted:
        files_deleted.append("processed")
    if not_found:
        files_not_found.append("processed")

    # 6. Delete video record from database
    db.delete(video)
    db.commit()

    return {"message": "El video ha sido eliminado exitosamente.", "video_id": str(video_id)}
