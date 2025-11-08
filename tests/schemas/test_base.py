"""Tests for base schemas"""
from datetime import datetime
from uuid import uuid4

from app.schemas.base import BaseSchema


class TestBaseSchema:
    """Tests for BaseSchema"""

    def test_base_schema_creation(self):
        """Test creating a BaseSchema instance"""
        test_id = uuid4()
        test_time = datetime.now()

        schema = BaseSchema(
            id=test_id,
            created_at=test_time,
            updated_at=test_time,
        )

        assert schema.id == test_id
        assert schema.created_at == test_time
        assert schema.updated_at == test_time

    def test_base_schema_from_attributes(self):
        """Test BaseSchema with from_attributes config"""

        class MockModel:
            def __init__(self):
                self.id = uuid4()
                self.created_at = datetime.now()
                self.updated_at = datetime.now()

        mock = MockModel()
        schema = BaseSchema.model_validate(mock)

        assert schema.id == mock.id
        assert schema.created_at == mock.created_at
        assert schema.updated_at == mock.updated_at

    def test_base_schema_config(self):
        """Test BaseSchema Config class"""
        assert BaseSchema.model_config.get("from_attributes") is True

    def test_base_schema_json_serialization(self):
        """Test JSON serialization of BaseSchema"""
        test_id = uuid4()
        test_time = datetime.now()

        schema = BaseSchema(
            id=test_id,
            created_at=test_time,
            updated_at=test_time,
        )

        json_data = schema.model_dump()
        assert "id" in json_data
        assert "created_at" in json_data
        assert "updated_at" in json_data
