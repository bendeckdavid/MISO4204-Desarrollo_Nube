"""Base schemas with common fields"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BaseSchema(BaseModel):
    """Base schema with common response fields"""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
