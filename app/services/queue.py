"""SQS Queue Service for video processing - Entrega 4"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class SQSService:
    """Service for interacting with AWS SQS for video processing tasks"""

    def __init__(self):
        """Initialize SQS client and queue configuration"""
        # Support LocalStack endpoint
        endpoint_url = os.getenv("AWS_ENDPOINT_URL")
        
        if endpoint_url:
            # LocalStack mode
            self.sqs = boto3.client(
                "sqs",
                region_name=settings.AWS_REGION,
                endpoint_url=endpoint_url,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
            )
        else:
            # Production mode - use IAM Role
            self.sqs = boto3.client("sqs", region_name=settings.AWS_REGION)
        
        self.queue_url = settings.SQS_QUEUE_URL
        self.dlq_url = settings.SQS_DLQ_URL

        logger.info(f"SQS Service initialized with queue: {self.queue_url}")

    def send_message(
        self, video_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Send a video processing task to the SQS queue

        Args:
            video_id: Unique identifier for the video to process
            metadata: Optional additional metadata about the video

        Returns:
            Message ID if successful, None if failed

        Raises:
            ClientError: If there's an error sending the message to SQS
        """
        try:
            message_body = {"video_id": video_id, "metadata": metadata or {}}

            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body),
                MessageAttributes={"VideoId": {"StringValue": video_id, "DataType": "String"}},
            )

            message_id = response.get("MessageId")
            logger.info(f"Sent message for video {video_id}, MessageId: {message_id}")
            return message_id

        except ClientError as e:
            logger.error(f"Failed to send message for video {video_id}: {e}")
            raise

    def receive_messages(self, max_messages: int = 1, wait_time: int = 20) -> List[Dict[str, Any]]:
        """
        Receive messages from the SQS queue (long polling)

        Args:
            max_messages: Maximum number of messages to receive (1-10)
            wait_time: Long polling wait time in seconds (0-20)

        Returns:
            List of message dictionaries

        Raises:
            ClientError: If there's an error receiving messages from SQS
        """
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time,  # Enable long polling
                MessageAttributeNames=["All"],
                AttributeNames=["All"],
            )

            messages = response.get("Messages", [])
            logger.debug(f"Received {len(messages)} message(s) from queue")
            return messages

        except ClientError as e:
            logger.error(f"Failed to receive messages: {e}")
            raise

    def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete a message from the queue after successful processing

        Args:
            receipt_handle: Receipt handle from the received message

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
            logger.debug(f"Deleted message with receipt handle: {receipt_handle[:50]}...")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete message: {e}")
            return False

    def change_visibility_timeout(self, receipt_handle: str, timeout: int) -> bool:
        """
        Extend the visibility timeout of a message being processed

        Args:
            receipt_handle: Receipt handle from the received message
            timeout: New visibility timeout in seconds (0-43200)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.sqs.change_message_visibility(
                QueueUrl=self.queue_url, ReceiptHandle=receipt_handle, VisibilityTimeout=timeout
            )
            logger.debug(f"Extended visibility timeout to {timeout}s")
            return True

        except ClientError as e:
            logger.error(f"Failed to change visibility timeout: {e}")
            return False

    def get_queue_attributes(self) -> Dict[str, Any]:
        """
        Get queue attributes including approximate number of messages

        Returns:
            Dictionary with queue attributes
        """
        try:
            response = self.sqs.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=[
                    "ApproximateNumberOfMessages",
                    "ApproximateNumberOfMessagesNotVisible",
                    "ApproximateNumberOfMessagesDelayed",
                ],
            )
            return response.get("Attributes", {})

        except ClientError as e:
            logger.error(f"Failed to get queue attributes: {e}")
            return {}

    def get_dlq_messages_count(self) -> int:
        """
        Get the number of messages in the Dead Letter Queue

        Returns:
            Number of messages in DLQ
        """
        try:
            response = self.sqs.get_queue_attributes(
                QueueUrl=self.dlq_url, AttributeNames=["ApproximateNumberOfMessages"]
            )
            count = int(response.get("Attributes", {}).get("ApproximateNumberOfMessages", 0))
            logger.info(f"DLQ has {count} message(s)")
            return count

        except ClientError as e:
            logger.error(f"Failed to get DLQ message count: {e}")
            return 0


# Singleton instance
sqs_service = SQSService()
