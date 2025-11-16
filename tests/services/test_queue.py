"""Tests for SQS Queue Service"""

import json

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from app.core.config import settings
from app.services.queue import SQSService


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for moto"""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def sqs_queues(aws_credentials):
    """Create mock SQS queues"""
    with mock_aws():
        # Create SQS client
        sqs = boto3.client("sqs", region_name="us-east-1")

        # Create main queue
        main_queue = sqs.create_queue(
            QueueName="test-video-processing-queue",
            Attributes={
                "VisibilityTimeout": "900",
                "MessageRetentionPeriod": "345600",
                "ReceiveMessageWaitTimeSeconds": "20",
            },
        )
        main_queue_url = main_queue["QueueUrl"]

        # Create DLQ
        dlq = sqs.create_queue(
            QueueName="test-video-processing-dlq",
            Attributes={"MessageRetentionPeriod": "1209600"},
        )
        dlq_url = dlq["QueueUrl"]

        yield {
            "main_queue_url": main_queue_url,
            "dlq_url": dlq_url,
            "sqs_client": sqs,
        }


@pytest.fixture
def sqs_service(sqs_queues, monkeypatch):
    """Create SQSService instance with mock queues"""
    monkeypatch.setattr(settings, "SQS_QUEUE_URL", sqs_queues["main_queue_url"])
    monkeypatch.setattr(settings, "SQS_DLQ_URL", sqs_queues["dlq_url"])
    monkeypatch.setattr(settings, "AWS_REGION", "us-east-1")

    service = SQSService()
    return service


class TestSQSServiceSendMessage:
    """Tests for send_message method"""

    def test_send_message_success(self, sqs_service, sqs_queues):
        """Test successful message sending"""
        video_id = "test-video-123"
        metadata = {"title": "Test Video", "user_id": "user-456"}

        message_id = sqs_service.send_message(video_id, metadata)

        assert message_id is not None
        assert isinstance(message_id, str)

        # Verify message is in queue
        messages = sqs_queues["sqs_client"].receive_message(
            QueueUrl=sqs_queues["main_queue_url"], MaxNumberOfMessages=1
        )

        assert "Messages" in messages
        assert len(messages["Messages"]) == 1

        body = json.loads(messages["Messages"][0]["Body"])
        assert body["video_id"] == video_id
        assert body["metadata"] == metadata

    def test_send_message_with_metadata(self, sqs_service, sqs_queues):
        """Test sending message with custom metadata"""
        video_id = "video-789"
        metadata = {"title": "Custom Video", "user_id": "user-999", "extra_field": "value"}

        message_id = sqs_service.send_message(video_id, metadata)

        assert message_id is not None

        # Receive and verify
        messages = sqs_queues["sqs_client"].receive_message(
            QueueUrl=sqs_queues["main_queue_url"], MessageAttributeNames=["All"]
        )

        assert "Messages" in messages
        message = messages["Messages"][0]

        # Check body
        body = json.loads(message["Body"])
        assert body["metadata"]["extra_field"] == "value"

        # Check message attributes
        assert "VideoId" in message["MessageAttributes"]
        assert message["MessageAttributes"]["VideoId"]["StringValue"] == video_id

    def test_send_message_without_metadata(self, sqs_service, sqs_queues):
        """Test sending message without metadata"""
        video_id = "video-no-meta"

        message_id = sqs_service.send_message(video_id)

        assert message_id is not None

        messages = sqs_queues["sqs_client"].receive_message(QueueUrl=sqs_queues["main_queue_url"])

        body = json.loads(messages["Messages"][0]["Body"])
        assert body["video_id"] == video_id
        assert body["metadata"] == {}


class TestSQSServiceReceiveMessages:
    """Tests for receive_messages method"""

    def test_receive_messages_empty_queue(self, sqs_service):
        """Test receiving from empty queue"""
        messages = sqs_service.receive_messages(max_messages=1, wait_time=0)

        assert messages == []

    def test_receive_single_message(self, sqs_service, sqs_queues):
        """Test receiving a single message"""
        # Send a message first
        video_id = "receive-test-1"
        sqs_service.send_message(video_id, {"test": "data"})

        # Receive message
        messages = sqs_service.receive_messages(max_messages=1, wait_time=0)

        assert len(messages) == 1
        assert "Body" in messages[0]
        assert "ReceiptHandle" in messages[0]

        body = json.loads(messages[0]["Body"])
        assert body["video_id"] == video_id

    def test_receive_multiple_messages(self, sqs_service, sqs_queues):
        """Test receiving multiple messages"""
        # Send 5 messages
        for i in range(5):
            sqs_service.send_message(f"video-{i}", {"index": i})

        # Receive up to 3 messages
        messages = sqs_service.receive_messages(max_messages=3, wait_time=0)

        assert len(messages) == 3

        # Verify all are unique
        video_ids = [json.loads(msg["Body"])["video_id"] for msg in messages]
        assert len(set(video_ids)) == 3

    def test_receive_message_attributes(self, sqs_service, sqs_queues):
        """Test receiving message with attributes"""
        video_id = "attr-test"
        sqs_service.send_message(video_id)

        messages = sqs_service.receive_messages(max_messages=1, wait_time=0)

        assert len(messages) == 1
        message = messages[0]

        # Check attributes exist
        assert "Attributes" in message
        assert "MessageAttributes" in message
        assert "VideoId" in message["MessageAttributes"]


class TestSQSServiceDeleteMessage:
    """Tests for delete_message method"""

    def test_delete_message_success(self, sqs_service, sqs_queues):
        """Test successful message deletion"""
        # Send and receive message
        sqs_service.send_message("delete-test")
        messages = sqs_service.receive_messages(max_messages=1, wait_time=0)

        receipt_handle = messages[0]["ReceiptHandle"]

        # Delete message
        result = sqs_service.delete_message(receipt_handle)

        assert result is True

        # Verify queue is empty (no messages visible)
        attrs = sqs_queues["sqs_client"].get_queue_attributes(
            QueueUrl=sqs_queues["main_queue_url"],
            AttributeNames=["ApproximateNumberOfMessages"],
        )
        assert attrs["Attributes"]["ApproximateNumberOfMessages"] == "0"

    def test_delete_message_invalid_handle(self, sqs_service):
        """Test deleting with invalid receipt handle"""
        # Should return False on error
        result = sqs_service.delete_message("invalid-receipt-handle")

        assert result is False


class TestSQSServiceChangeVisibility:
    """Tests for change_visibility_timeout method"""

    def test_change_visibility_success(self, sqs_service, sqs_queues):
        """Test changing visibility timeout"""
        # Send and receive message
        sqs_service.send_message("visibility-test")
        messages = sqs_service.receive_messages(max_messages=1, wait_time=0)

        receipt_handle = messages[0]["ReceiptHandle"]

        # Change visibility to 60 seconds
        result = sqs_service.change_visibility_timeout(receipt_handle, 60)

        assert result is True

    def test_change_visibility_invalid_handle(self, sqs_service):
        """Test changing visibility with invalid handle"""
        result = sqs_service.change_visibility_timeout("invalid-handle", 60)

        assert result is False


class TestSQSServiceQueueAttributes:
    """Tests for get_queue_attributes method"""

    def test_get_queue_attributes_empty(self, sqs_service):
        """Test getting attributes of empty queue"""
        attrs = sqs_service.get_queue_attributes()

        assert isinstance(attrs, dict)
        assert "ApproximateNumberOfMessages" in attrs
        assert int(attrs["ApproximateNumberOfMessages"]) == 0

    def test_get_queue_attributes_with_messages(self, sqs_service):
        """Test getting attributes with messages in queue"""
        # Send 3 messages
        for i in range(3):
            sqs_service.send_message(f"attr-msg-{i}")

        attrs = sqs_service.get_queue_attributes()

        assert int(attrs["ApproximateNumberOfMessages"]) == 3
        assert "ApproximateNumberOfMessagesNotVisible" in attrs
        assert "ApproximateNumberOfMessagesDelayed" in attrs


class TestSQSServiceDLQMessages:
    """Tests for get_dlq_messages_count method"""

    def test_dlq_count_empty(self, sqs_service):
        """Test DLQ count when empty"""
        count = sqs_service.get_dlq_messages_count()

        assert count == 0

    def test_dlq_count_with_messages(self, sqs_service, sqs_queues):
        """Test DLQ count with messages"""
        # Send messages directly to DLQ
        for i in range(2):
            sqs_queues["sqs_client"].send_message(
                QueueUrl=sqs_queues["dlq_url"], MessageBody=json.dumps({"test": i})
            )

        count = sqs_service.get_dlq_messages_count()

        assert count == 2


class TestSQSServiceIntegration:
    """Integration tests for complete workflows"""

    def test_send_receive_delete_workflow(self, sqs_service):
        """Test complete workflow: send -> receive -> process -> delete"""
        # 1. Send message
        video_id = "workflow-test"
        metadata = {"title": "Workflow Video"}

        message_id = sqs_service.send_message(video_id, metadata)
        assert message_id is not None

        # 2. Receive message
        messages = sqs_service.receive_messages(max_messages=1, wait_time=0)
        assert len(messages) == 1

        message = messages[0]
        body = json.loads(message["Body"])
        assert body["video_id"] == video_id

        # 3. Process (simulate)
        receipt_handle = message["ReceiptHandle"]

        # 4. Delete after successful processing
        delete_result = sqs_service.delete_message(receipt_handle)
        assert delete_result is True

        # 5. Verify queue is empty
        attrs = sqs_service.get_queue_attributes()
        assert int(attrs["ApproximateNumberOfMessages"]) == 0

    def test_visibility_timeout_workflow(self, sqs_service):
        """Test workflow with visibility timeout extension"""
        # Send message
        sqs_service.send_message("timeout-test")

        # Receive (becomes invisible)
        messages = sqs_service.receive_messages(max_messages=1, wait_time=0)
        receipt_handle = messages[0]["ReceiptHandle"]

        # Extend visibility (simulate long processing)
        result = sqs_service.change_visibility_timeout(receipt_handle, 300)
        assert result is True

        # Delete after processing
        delete_result = sqs_service.delete_message(receipt_handle)
        assert delete_result is True

    def test_multiple_workers_simulation(self, sqs_service):
        """Test simulation of multiple workers processing"""
        # Send 10 messages
        for i in range(10):
            sqs_service.send_message(f"multi-worker-{i}", {"index": i})

        # Worker 1: Receive 5 messages
        worker1_messages = sqs_service.receive_messages(max_messages=5, wait_time=0)
        assert len(worker1_messages) == 5

        # Worker 2: Receive remaining messages
        worker2_messages = sqs_service.receive_messages(max_messages=5, wait_time=0)
        assert len(worker2_messages) == 5

        # Verify no overlap (each message received by one worker)
        worker1_ids = [json.loads(msg["Body"])["video_id"] for msg in worker1_messages]
        worker2_ids = [json.loads(msg["Body"])["video_id"] for msg in worker2_messages]

        assert len(set(worker1_ids) & set(worker2_ids)) == 0  # No intersection

        # Both workers process and delete
        for msg in worker1_messages + worker2_messages:
            sqs_service.delete_message(msg["ReceiptHandle"])

        # Verify all processed
        attrs = sqs_service.get_queue_attributes()
        assert int(attrs["ApproximateNumberOfMessages"]) == 0


class TestSQSServiceErrorHandling:
    """Tests for error handling"""

    def test_send_message_with_exception(self, sqs_service, monkeypatch):
        """Test error handling when SQS is unavailable"""

        def mock_send_message(*args, **kwargs):
            raise ClientError({"Error": {"Code": "ServiceUnavailable"}}, "SendMessage")

        monkeypatch.setattr(sqs_service.sqs, "send_message", mock_send_message)

        with pytest.raises(ClientError):
            sqs_service.send_message("error-test")

    def test_receive_messages_with_exception(self, sqs_service, monkeypatch):
        """Test error handling when receive fails"""

        def mock_receive_message(*args, **kwargs):
            raise ClientError({"Error": {"Code": "ServiceUnavailable"}}, "ReceiveMessage")

        monkeypatch.setattr(sqs_service.sqs, "receive_message", mock_receive_message)

        with pytest.raises(ClientError):
            sqs_service.receive_messages()
