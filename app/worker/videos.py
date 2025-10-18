"""Celery tasks - TEMPLATE"""

from app.worker.celery_app import celery_app


# A Celery task named "process_video" that do the following:
# - receives a video id
# - get the video location from the videos table on the database
# - load the video file from disk
# - process the video to trim it to the first 30 seconds, update its resolution to 720p and add a watermark
# - save the processed video to a new file on disk
# - update the videos table with the new file location and set its status to "processed"
# - handle any errors that may occur during the process and update the video status to "failed" if necessary
@celery_app.task(bind=True, max_retries=3)
def process_video(self, video_id: str):
    """Process video task"""

    print("START Processing video task. Video ID:", video_id)
