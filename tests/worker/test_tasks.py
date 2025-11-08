"""Tests for Celery tasks"""
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
