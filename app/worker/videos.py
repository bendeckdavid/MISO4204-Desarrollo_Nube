"""Celery tasks - Video processing"""

import os
from app.db.database import SessionLocal
from app.worker.celery_app import celery_app
from app.db.models import Video
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip


@celery_app.task(bind=True, max_retries=3)
def process_video(self, video_id: str):
    """Process video task with proper database session management"""
    print(f"Processing video task started for video ID: {video_id}")

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

        # Validate file paths exist
        if not os.path.exists(video.original_file_path):
            raise FileNotFoundError(f"Original video file not found: {video.original_file_path}")

        # Ensure processed file directory exists
        processed_dir = os.path.dirname(video.processed_file_path)
        os.makedirs(processed_dir, exist_ok=True)

        # Process the video to trim it to the first 30 seconds, update its resolution to 720p
        # and add a watermark using moviepy
        clip = VideoFileClip(video.original_file_path).subclip(0, 30)
        clip = clip.resize(height=720)
        watermark = TextClip(
            "Sample Watermark", fontsize=24, color="white", bg_color="black", size=(clip.w, 30)
        )
        watermark = watermark.set_pos(("center", "bottom")).set_duration(clip.duration)
        final_clip = CompositeVideoClip([clip, watermark])

        # Save the processed video to a new file on disk
        print(f"Writing processed video to: {video.processed_file_path}")
        final_clip.write_videofile(
            video.processed_file_path,
            codec="libx264",
            audio_codec="aac",
            verbose=False,
            logger=None,  # Suppress moviepy logs
        )

        # Clean up moviepy objects to free memory
        final_clip.close()
        clip.close()

        # Update the videos table with the new file location and set its status to "processed"
        video.status = "processed"
        db.commit()

        return {"status": "success", "message": f"Video {video_id} processed successfully"}

    except Exception as e:
        print(f"Error processing video ID {video_id}: {e}")

        # Update video status to failed
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = "failed"
                db.commit()
        except Exception as db_error:
            print(f"Failed to update video status: {db_error}")

        # Retry the task with exponential backoff
        raise self.retry(exc=e, countdown=60, max_retries=3)

    finally:
        # Always close the database session
        db.close()
