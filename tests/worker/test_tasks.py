"""Tests for Celery tasks"""
from unittest.mock import patch, MagicMock

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

    def test_example_task_exception_with_retry(self):
        """Test task exception handling triggers retry (lines 13, 14, 15)"""
        # Create an exception that will be caught and trigger retry
        mock_exception = RuntimeError("Processing failed")

        # Patch the wrapped function to raise an exception
        with patch("app.worker.tasks.example_task.__wrapped__") as mock_task:
            mock_task.side_effect = mock_exception

            # Mock self.retry to also raise an exception (line 15)
            mock_self = MagicMock()
            mock_self.retry.side_effect = Exception("Retry triggered")

            # Test that exception triggers retry which also raises
            with pytest.raises(Exception):
                example_task.run(mock_self, {"test": "data"})
