"""Celery tasks - Video processing"""

import os
from app.db.database import SessionLocal
from app.worker.celery_app import celery_app
from app.db.models import Video
from app.core.config import settings
from moviepy import VideoFileClip, TextClip, CompositeVideoClip


def resolve_container_path(file_path: str, fallback_base_dir: str = "/app") -> str:
    """
    Resolve file paths to work within Docker container filesystem.

    Args:
        file_path: Original file path (can be absolute or relative)
        fallback_base_dir: Base directory to try if absolute path doesn't exist

    Returns:
        Resolved path that exists in the container

    Raises:
        FileNotFoundError: If file cannot be found in any expected location
    """
    if os.path.exists(file_path):
        return file_path

    if os.path.isabs(file_path):
        # Try relative to fallback base directory
        relative_path = file_path.lstrip("/")
        fallback_path = os.path.join(fallback_base_dir, relative_path)
        if os.path.exists(fallback_path):
            return fallback_path

    raise FileNotFoundError(f"File not found: {file_path}")


def ensure_directory_exists(file_path: str, fallback_base_dir: str = "/app") -> str:
    """
    Ensure directory exists for the given file path, with container-aware fallback.

    Args:
        file_path: Target file path
        fallback_base_dir: Base directory to use as fallback

    Returns:
        Final directory path that was created/exists
    """
    directory = os.path.dirname(file_path)

    try:
        os.makedirs(directory, exist_ok=True)
        return file_path
    except PermissionError:
        # Try fallback to base directory
        if os.path.isabs(file_path):
            relative_path = file_path.lstrip("/")
            fallback_path = os.path.join(fallback_base_dir, relative_path)
            fallback_dir = os.path.dirname(fallback_path)
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_path
        raise


@celery_app.task(bind=True, max_retries=3)
def process_video(self, video_id: str):
    """Process video task with proper database session management"""

    # Create database session for Celery task
    db = SessionLocal()

    try:
        # Get the video record from the database
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return {"status": "failed", "error": "Video not found"}

        # Update status to processing
        video.status = "processing"
        db.commit()

        # Resolve file paths within the container filesystem
        container_original_path = resolve_container_path(
            video.original_file_path, settings.APP_BASE_DIR
        )

        # Validate file permissions
        if not os.access(container_original_path, os.R_OK):
            raise PermissionError(f"Cannot read original video file: {container_original_path}")

        # Ensure processed file directory exists and get the final path
        container_processed_path = ensure_directory_exists(
            video.processed_file_path, settings.APP_BASE_DIR
        )

        # Process the video to trim it to the first 30 seconds (or full duration if shorter),
        # update its resolution to 720p and add a watermark using moviepy
        original_clip = VideoFileClip(container_original_path)
        trim_duration = min(30, original_clip.duration)
        clip = original_clip.subclipped(0, trim_duration)
        clip = clip.resized(height=720)
        watermark = (
            TextClip(text="ANF Rising Stars Showcase", font_size=36, color="white")
            .with_position(("center", "bottom"))
            .with_duration(clip.duration)
        )
        final_clip = CompositeVideoClip([clip, watermark])

        # Save the processed video to a new file on disk
        final_clip.write_videofile(container_processed_path, codec="libx264", audio_codec="aac")

        # Clean up moviepy objects to free memory
        final_clip.close()
        clip.close()
        original_clip.close()

        # Update the videos table with the final processed file path and set status to "processed"
        # Store the container path that was actually used
        video.processed_file_path = container_processed_path
        video.status = "processed"
        db.commit()

        return {"status": "success", "message": f"Video {video_id} processed successfully"}

    except Exception as e:

        # Update video status to failed
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = "failed"
                db.commit()
        except Exception as db_error:
            # Log database error but continue with retry
            print(f"Database error while updating status to failed: {db_error}")

        # Retry the task with exponential backoff
        raise self.retry(exc=e, countdown=60, max_retries=3)

    finally:
        # Always close the database session
        db.close()
