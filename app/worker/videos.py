"""Video processing tasks for SQS worker (Entrega 4)"""

import logging
import os
import tempfile

from moviepy import CompositeVideoClip, TextClip, VideoFileClip

from app.core.config import settings
from app.core.storage import storage
from app.db.database import SessionLocal
from app.db.models import Video

logger = logging.getLogger(__name__)


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


def _setup_file_paths(video, settings):
    """
    Setup file paths for video processing based on storage backend.

    Returns:
        tuple: (original_path, processed_path, temp_original, temp_processed)
    """
    temp_original = None
    temp_processed = None

    if settings.STORAGE_BACKEND == "s3":
        # S3: Download to temp files for processing
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".mp4"
        ) as temp_orig, tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_proc:
            temp_original = temp_orig.name
            temp_processed = temp_proc.name

            # Download original from S3
            original_data = storage.download_file(video.original_file_path)
            temp_orig.write(original_data)
            temp_orig.flush()

        return temp_original, temp_processed, temp_original, temp_processed
    else:
        # Local: Use resolve_container_path for local filesystem
        original_path = resolve_container_path(video.original_file_path, settings.APP_BASE_DIR)

        # Validate file permissions
        if not os.access(original_path, os.R_OK):
            raise PermissionError(f"Cannot read original video file: {original_path}")

        # Ensure processed file directory exists
        processed_path = ensure_directory_exists(video.processed_file_path, settings.APP_BASE_DIR)

        return original_path, processed_path, None, None


def _process_video_file(original_path, processed_path):
    """
    Apply video transformations using moviepy.

    Returns:
        None (writes to processed_path)
    """
    original_clip = VideoFileClip(original_path)
    trim_duration = min(30, original_clip.duration)
    clip = original_clip.subclipped(0, trim_duration)
    clip = clip.resized(height=720)
    watermark = (
        TextClip(text="ANF Rising Stars Showcase", font_size=36, color="white")
        .with_position(("center", "bottom"))
        .with_duration(clip.duration)
    )
    final_clip = CompositeVideoClip([clip, watermark])

    # Save the processed video
    final_clip.write_videofile(processed_path, codec="libx264", audio_codec="aac")

    # Clean up moviepy objects to free memory
    final_clip.close()
    clip.close()
    original_clip.close()


def _cleanup_temp_files(temp_original, temp_processed):
    """Clean up temporary files if they exist."""
    if temp_original and os.path.exists(temp_original):
        try:
            os.unlink(temp_original)
        except Exception:
            pass
    if temp_processed and os.path.exists(temp_processed):
        try:
            os.unlink(temp_processed)
        except Exception:
            pass


def process_video_sync(video_id: str) -> dict:
    """
    Process video - synchronous version for SQS worker (Entrega 4)

    Supports both local and S3 storage backends.
    For S3: Downloads to temp, processes, uploads back to S3
    For local: Processes directly on disk

    Args:
        video_id: UUID of the video to process

    Returns:
        dict with status and message/error
    """
    db = SessionLocal()
    temp_original = None
    temp_processed = None

    try:
        # Get the video record from the database
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return {"status": "failed", "error": "Video not found"}

        # Update status to processing
        video.status = "processing"
        db.commit()

        logger.info(f"Starting processing for video {video_id}")

        # Setup file paths based on storage backend
        original_path, processed_path, temp_original, temp_processed = _setup_file_paths(
            video, settings
        )

        # Process the video
        _process_video_file(original_path, processed_path)

        # Upload processed video if using S3
        if settings.STORAGE_BACKEND == "s3":
            logger.info(f"Uploading processed video to S3: {video.processed_file_path}")
            with open(processed_path, "rb") as f:
                processed_data = f.read()
            storage.upload_file(processed_data, video.processed_file_path)

        # Update the videos table
        video.status = "processed"
        video.is_published = True
        db.commit()

        logger.info(f"Successfully processed video {video_id}")
        return {"status": "success", "message": f"Video {video_id} processed successfully"}

    except Exception as e:
        logger.error(f"Error processing video {video_id}: {e}", exc_info=True)

        # Update video status to failed
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = "failed"
                db.commit()
        except Exception as db_error:
            logger.error(f"Database error while updating status to failed: {db_error}")

        return {"status": "failed", "error": str(e)}

    finally:
        _cleanup_temp_files(temp_original, temp_processed)
        db.close()
