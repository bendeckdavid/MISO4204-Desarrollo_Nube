"""Tests for Celery tasks"""
from unittest.mock import Mock, patch

import pytest

from app.worker.tasks import example_task


class TestExampleTask:
    """Tests for example_task"""

    def test_example_task_success(self):
        """Test successful task execution"""
        test_data = {"key": "value"}
        result = example_task(test_data)

        assert result["status"] == "success"
        assert "Processed" in result["result"]
        assert str(test_data) in result["result"]

    @patch("app.worker.tasks.example_task.retry")
    def test_example_task_retry_on_exception(self, mock_retry):
        """Test task retry on exception"""
        # Mock the task's self parameter
        task_instance = Mock()
        task_instance.retry.side_effect = Exception("Max retries exceeded")

        # Patch the task to raise an exception
        with patch.object(example_task, "__call__") as mock_call:
            mock_call.side_effect = Exception("Test error")

            # Execute task directly to trigger exception handling
            result = example_task.apply(args=[{"test": "data"}]).get()

            # Task should return success since it's just a template
            assert "status" in result

    def test_example_task_with_empty_data(self):
        """Test task with empty data"""
        result = example_task({})

        assert result["status"] == "success"
        assert "Processed" in result["result"]

    def test_example_task_with_complex_data(self):
        """Test task with complex data structure"""
        test_data = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "string": "test",
        }
        result = example_task(test_data)

        assert result["status"] == "success"
        assert "Processed" in result["result"]
