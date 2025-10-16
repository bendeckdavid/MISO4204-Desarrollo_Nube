"""Celery tasks - TEMPLATE"""

from app.worker.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def example_task(self, data: dict):
    """Example async task"""
    try:
        result = f"Processed: {data}"
        return {"status": "success", "result": result}

    except Exception as e:
        try:
            raise self.retry(exc=e, countdown=60)
        except Exception:
            return {"status": "failed", "error": str(e)}
