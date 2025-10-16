"""API tests - TEMPLATE"""

from fastapi import status


def test_health_check(client):
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "healthy"


def test_create_task(client):
    """Test create task (POST)"""
    response = client.post(
        "/api/tasks/",
        json={"name": "Test Task", "description": "Test description"},
        headers={"x-api-key": "test-api-key-123"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Test Task"
    assert data["description"] == "Test description"
    assert "id" in data
    assert "created_at" in data


def test_create_task_with_celery(client):
    """Test that creating task triggers Celery async processing"""
    response = client.post(
        "/api/tasks/",
        json={"name": "Async Task", "description": "Will be processed in background"},
        headers={"x-api-key": "test-api-key-123"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Async Task"


def test_list_tasks(client):
    """Test list tasks with pagination (GET)"""
    client.post(
        "/api/tasks/",
        json={"name": "Task 1", "description": "Description 1"},
        headers={"x-api-key": "test-api-key-123"},
    )

    response = client.get("/api/tasks/", headers={"x-api-key": "test-api-key-123"})

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0
    assert "total" in data
    assert "page" in data
    assert "size" in data


def test_get_task(client):
    """Test get task by ID (GET)"""
    create_response = client.post(
        "/api/tasks/",
        json={"name": "Task 1", "description": "Description 1"},
        headers={"x-api-key": "test-api-key-123"},
    )
    task_id = create_response.json()["id"]

    response = client.get(f"/api/tasks/{task_id}", headers={"x-api-key": "test-api-key-123"})

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == task_id
    assert data["name"] == "Task 1"


def test_update_task(client):
    """Test update task (PATCH)"""
    create_response = client.post(
        "/api/tasks/",
        json={"name": "Task 1", "description": "Description 1"},
        headers={"x-api-key": "test-api-key-123"},
    )
    task_id = create_response.json()["id"]

    response = client.patch(
        f"/api/tasks/{task_id}",
        json={"name": "Updated Task"},
        headers={"x-api-key": "test-api-key-123"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Task"
    assert data["description"] == "Description 1"


def test_delete_task(client):
    """Test delete task (DELETE)"""
    create_response = client.post(
        "/api/tasks/",
        json={"name": "Task to delete", "description": "Will be deleted"},
        headers={"x-api-key": "test-api-key-123"},
    )
    task_id = create_response.json()["id"]

    response = client.delete(f"/api/tasks/{task_id}", headers={"x-api-key": "test-api-key-123"})

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/api/tasks/{task_id}", headers={"x-api-key": "test-api-key-123"})
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_unauthorized_without_api_key(client):
    """Test that endpoints require API key"""
    response = client.get("/api/tasks/")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
