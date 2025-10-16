"""Database models - TEMPLATE"""

from sqlalchemy import Column, String

from app.db.base import Base


class Task(Base):
    """Task model - TEMPLATE"""

    __tablename__ = "tasks"

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    def __repr__(self):
        return f"<Task {self.name}>"
