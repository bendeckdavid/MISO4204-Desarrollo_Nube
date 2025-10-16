"""Task endpoints - TEMPLATE with CRUD + Celery example"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page, add_pagination, paginate
from sqlalchemy.orm import Session

from app.core.security import verify_api_key
from app.db import models
from app.db.database import get_db
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.worker.tasks import example_task

router = APIRouter()


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    Create new task and trigger background processing with Celery

    This endpoint saves the task to DB and immediately sends it to Celery
    for async processing.
    """
    # Save to database first
    task = models.Task(name=data.name, description=data.description)
    db.add(task)
    db.commit()
    db.refresh(task)

    # Send task to Celery worker for background processing
    example_task.apply_async(
        args=[{"id": task.id, "name": task.name, "description": task.description}]
    )

    return task


@router.get("/", response_model=Page[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    List all tasks with automatic pagination
    """
    tasks = db.query(models.Task).all()
    return paginate(tasks)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """Get task by ID"""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """Update task by ID"""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Update only provided fields
    if data.name is not None:
        task.name = data.name  # type: ignore
    if data.description is not None:
        task.description = data.description  # type: ignore

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)
):
    """Delete task by ID"""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    db.delete(task)
    db.commit()
    return None


# Add pagination support to this router
add_pagination(router)
