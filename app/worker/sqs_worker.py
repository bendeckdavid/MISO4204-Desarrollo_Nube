"""SQS Worker - Polls queue and processes videos (Entrega 4)"""

import json
import logging
import signal
import sys
import time

from app.core.config import settings
from app.services.queue import sqs_service
from app.worker.videos import process_video_sync

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def process_message(message: dict) -> bool:
    """
    Process a single SQS message

    Args:
        message: SQS message dictionary

    Returns:
        True if processing was successful, False otherwise
    """
    try:
        body = json.loads(message["Body"])
        video_id = body["video_id"]
        receipt_handle = message["ReceiptHandle"]

        logger.info(f"Processing video {video_id}")

        # Process video (synchronous function)
        result = process_video_sync(video_id)

        if result.get("status") == "success":
            # Delete message on success
            sqs_service.delete_message(receipt_handle)
            logger.info(f"Successfully processed video {video_id}")
            return True
        else:
            # Processing failed, but function returned
            # Let SQS retry (message will become visible again after timeout)
            logger.error(f"Processing failed for video {video_id}: {result.get('error')}")
            return False

    except json.JSONDecodeError as e:
        logger.error(f"Invalid message format: {e}")
        # Delete malformed message so it doesn't block the queue
        try:
            sqs_service.delete_message(message["ReceiptHandle"])
        except Exception:
            pass
        return False

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        # Let SQS retry by not deleting the message
        return False


def main():  # pragma: no cover
    """Main worker loop"""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("=" * 80)
    logger.info("Starting SQS Video Processing Worker (Entrega 4)")
    logger.info(f"Queue URL: {settings.SQS_QUEUE_URL}")
    logger.info(f"DLQ URL: {settings.SQS_DLQ_URL}")
    logger.info(f"Region: {settings.AWS_REGION}")
    logger.info("=" * 80)

    # Check initial queue status
    try:
        attrs = sqs_service.get_queue_attributes()
        logger.info("Queue status at startup:")
        logger.info(f"  - Messages available: {attrs.get('ApproximateNumberOfMessages', 0)}")
        logger.info(
            f"  - Messages in flight: {attrs.get('ApproximateNumberOfMessagesNotVisible', 0)}"
        )
        logger.info(f"  - Messages delayed: {attrs.get('ApproximateNumberOfMessagesDelayed', 0)}")

        dlq_count = sqs_service.get_dlq_messages_count()
        if dlq_count > 0:
            logger.warning(f"  - DLQ has {dlq_count} message(s) that need attention!")

    except Exception as e:
        logger.warning(f"Could not get initial queue status: {e}")

    consecutive_empty_polls = 0
    messages_processed = 0

    while not shutdown_requested:
        try:
            # Long polling (20 seconds)
            messages = sqs_service.receive_messages(max_messages=1, wait_time=20)

            if messages:
                consecutive_empty_polls = 0
                for message in messages:
                    if shutdown_requested:
                        logger.info("Shutdown requested, stopping message processing")
                        break

                    success = process_message(message)
                    if success:
                        messages_processed += 1

            else:
                consecutive_empty_polls += 1
                if consecutive_empty_polls % 3 == 0:  # Every 3 empty polls (~1 minute)
                    logger.debug(
                        f"No messages (empty polls: {consecutive_empty_polls}, "
                        f"total processed: {messages_processed})"
                    )

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            break

        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            # Sleep before retrying to avoid tight error loops
            time.sleep(5)

    logger.info("=" * 80)
    logger.info(f"Worker shutting down gracefully. Total messages processed: {messages_processed}")
    logger.info("=" * 80)
    sys.exit(0)


if __name__ == "__main__":  # pragma: no cover
    main()
