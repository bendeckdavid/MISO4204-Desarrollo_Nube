"""Tests for SQS worker main loop and message processing"""
import json
import signal
from unittest.mock import patch

from app.worker import sqs_worker


class TestSignalHandler:
    """Tests for signal_handler function"""

    def test_signal_handler_sets_shutdown_flag(self):
        """Test that signal handler sets shutdown_requested to True"""
        # Reset the flag
        sqs_worker.shutdown_requested = False

        # Call signal handler
        sqs_worker.signal_handler(signal.SIGTERM, None)

        # Verify flag is set
        assert sqs_worker.shutdown_requested is True


class TestProcessMessage:
    """Tests for process_message function"""

    @patch("app.worker.sqs_worker.sqs_service")
    @patch("app.worker.sqs_worker.process_video_sync")
    def test_process_message_success(self, mock_process_video, mock_sqs_service):
        """Test successful message processing"""
        message = {
            "Body": json.dumps({"video_id": "video123"}),
            "ReceiptHandle": "receipt123",
        }

        mock_process_video.return_value = {"status": "success"}

        result = sqs_worker.process_message(message)

        assert result is True
        mock_process_video.assert_called_once_with("video123")
        mock_sqs_service.delete_message.assert_called_once_with("receipt123")

    @patch("app.worker.sqs_worker.sqs_service")
    @patch("app.worker.sqs_worker.process_video_sync")
    def test_process_message_processing_failed(self, mock_process_video, mock_sqs_service):
        """Test message processing when video processing fails"""
        message = {
            "Body": json.dumps({"video_id": "video123"}),
            "ReceiptHandle": "receipt123",
        }

        mock_process_video.return_value = {
            "status": "failed",
            "error": "Processing error",
        }

        result = sqs_worker.process_message(message)

        assert result is False
        mock_process_video.assert_called_once_with("video123")
        # Message should NOT be deleted on failure (let SQS retry)
        mock_sqs_service.delete_message.assert_not_called()

    @patch("app.worker.sqs_worker.sqs_service")
    @patch("app.worker.sqs_worker.process_video_sync")
    def test_process_message_invalid_json(self, mock_process_video, mock_sqs_service):
        """Test processing message with invalid JSON"""
        message = {
            "Body": "invalid json{",
            "ReceiptHandle": "receipt123",
        }

        result = sqs_worker.process_message(message)

        assert result is False
        mock_process_video.assert_not_called()
        # Malformed messages should be deleted to avoid blocking queue
        mock_sqs_service.delete_message.assert_called_once_with("receipt123")

    @patch("app.worker.sqs_worker.sqs_service")
    @patch("app.worker.sqs_worker.process_video_sync")
    def test_process_message_exception(self, mock_process_video, mock_sqs_service):
        """Test processing message when exception occurs"""
        message = {
            "Body": json.dumps({"video_id": "video123"}),
            "ReceiptHandle": "receipt123",
        }

        mock_process_video.side_effect = Exception("Unexpected error")

        result = sqs_worker.process_message(message)

        assert result is False
        # Message should NOT be deleted on exception (let SQS retry)
        mock_sqs_service.delete_message.assert_not_called()

    @patch("app.worker.sqs_worker.sqs_service")
    @patch("app.worker.sqs_worker.process_video_sync")
    def test_process_message_invalid_json_delete_fails(self, mock_process_video, mock_sqs_service):
        """Test processing message with invalid JSON when delete fails"""
        message = {
            "Body": "invalid json{",
            "ReceiptHandle": "receipt123",
        }

        # Make delete raise exception
        mock_sqs_service.delete_message.side_effect = Exception("Delete failed")

        result = sqs_worker.process_message(message)

        assert result is False
        mock_process_video.assert_not_called()
        # Should still try to delete despite exception
        mock_sqs_service.delete_message.assert_called_once_with("receipt123")
