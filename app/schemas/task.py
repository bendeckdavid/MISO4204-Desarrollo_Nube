"""Pydantic schemas - TEMPLATE"""

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class TaskCreate(BaseModel):
    """Schema for creating task"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class TaskUpdate(BaseModel):
    """Schema for updating task"""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class TaskResponse(BaseSchema):
    """Schema for task response"""

    name: str
    description: str | None
