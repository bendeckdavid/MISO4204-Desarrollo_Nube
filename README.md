# FastAPI Template - Scalable REST API

A production-ready FastAPI template with PostgreSQL, Celery, Redis, and Docker. Built with modern Python patterns and best practices.

## 🚀 Features

- ✅ **FastAPI** - Modern, fast web framework for building APIs
- ✅ **PostgreSQL** - Reliable relational database with UUID primary keys
- ✅ **SQLAlchemy 2.0** - Async ORM with base models for DRY code
- ✅ **Celery + Redis** - Distributed task queue for background processing
- ✅ **Docker Compose** - Multi-container orchestration
- ✅ **Pydantic v2** - Data validation with base schemas
- ✅ **fastapi-pagination** - Automatic pagination support
- ✅ **Poetry** - Modern dependency management
- ✅ **pytest** - Comprehensive test suite (88% coverage)
- ✅ **Pre-commit hooks** - Code quality (Black, Flake8, isort, mypy)
- ✅ **API Key Authentication** - Simple security out of the box

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Architecture](#-architecture)
- [API Documentation](#-api-documentation)
- [Development](#-development)
- [Testing](#-testing)
- [Code Quality](#-code-quality)
- [Docker Commands](#-docker-commands)
- [Deployment](#-deployment)

## 🏃 Quick Start

### Prerequisites

- Docker >= 20.10
- Docker Compose >= 2.0
- Python 3.13+ (for local development)

### 1. Clone and Setup

```bash
# Clone the repository
git clone git@github.com:bendeckdavid/MISO4204-Desarrollo_Nube.git

# Copy environment variables
cp .env.example .env

# Edit .env with your values (optional for development)
```

### 2. Start Services

```bash
# Build and start all services
docker-compose up --build -d

# Wait for services to be ready (~15 seconds)
docker-compose ps
```

You should see:
```
     Name                   Command                  State                        Ports                  
---------------------------------------------------------------------------------------------------------
fastapi_api      uvicorn app.main:app --hos ...   Up             0.0.0.0:8000->8000/tcp,:::8000->8000/tcp
fastapi_db       docker-entrypoint.sh postgres    Up (healthy)   0.0.0.0:5433->5432/tcp,:::5433->5432/tcp
fastapi_redis    docker-entrypoint.sh redis ...   Up (healthy)   0.0.0.0:6380->6379/tcp,:::6380->6379/tcp
fastapi_worker   celery -A app.worker.celer ...   Up             8000/tcp              
```

### 3. Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Load sample data
docker-compose exec api python scripts/load_data.py

# Run tests
docker-compose exec api pytest -v
```

### 4. Access Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📁 Project Structure

```
.
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py          # Health check endpoint
│   │       └── tasks.py            # CRUD + Celery example
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Settings (Pydantic)
│   │   └── security.py             # API Key authentication
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base model (UUID, timestamps)
│   │   ├── database.py             # SQLAlchemy setup
│   │   └── models.py               # Database models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base Pydantic schema
│   │   └── task.py                 # Task schemas (Create, Update, Response)
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── celery_app.py           # Celery configuration
│   │   └── tasks.py                # Async tasks
│   └── main.py                     # FastAPI application entry point
├── tests/
│   ├── api/
│   │   └── test_example.py         # API tests
│   └── conftest.py                 # Test fixtures
├── scripts/
│   └── load_data.py                # Sample data loader
├── .env.example                    # Environment variables template
├── .pre-commit-config.yaml         # Pre-commit hooks config
├── docker-compose.yml              # Docker services orchestration
├── Dockerfile                      # API & Worker image
├── pyproject.toml                  # Poetry dependencies & config
└── README.md                       # This file
```

### Key Components

#### Base Model (`app/db/base.py`)
All models inherit from this base class:
```python
class Base(SQLAlchemyBase):
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### Base Schema (`app/schemas/base.py`)
Common response fields for all schemas:
```python
class BaseSchema(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

## 🏗️ Architecture

### 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                           │
│  (FastAPI Routes - app/api/routes/)                         │
│  • Request validation (Pydantic)                            │
│  • Response serialization                                   │
│  • Authentication (API Key)                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      Business Logic                         │
│  (Direct in routes - can be extracted to services layer)    │
│  • CRUD operations                                          │
│  • Celery task submission                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      Data Layer                             │
│  (SQLAlchemy ORM - app/db/)                                 │
│  • Database models                                          │
│  • Query execution                                          │
└─────────────────────────────────────────────────────────────┘
```

### Celery Worker Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   FastAPI   │         │    Redis    │         │   Celery    │
│     API     │────────▶│   (Broker)  │────────▶│   Worker    │
└─────────────┘         └─────────────┘         └─────────────┘
      │                        │                        │
      │ 1. Submit task         │ 2. Queue task          │ 3. Process task
      │                        │                        │
      ▼                        ▼                        ▼
 Returns immediately      Stores task              Executes async
 (non-blocking)           (distributed)            (background)
```

**Flow:**
1. API receives POST request with data
2. Saves record to PostgreSQL (synchronous)
3. Submits task to Celery via Redis (non-blocking)
4. Returns response immediately
5. Worker picks up task from Redis queue
6. Worker processes task in background
7. Result stored in Redis (optional)

### Docker Services

```
┌──────────────────────────────────────────────────────────────┐
│  Docker Compose Network (app_network)                        │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │   fastapi  │  │ PostgreSQL │  │   Redis    │              │
│  │    _api    │─▶│   _db      │  │   _redis   │              │
│  │  :8000     │  │  :5433     │  │  :6380     │              │
│  └─────┬──────┘  └────────────┘  └──────▲─────┘              │
│        │                                  │                  │
│        │         ┌────────────────────────┘                  │
│        │         │                                           │
│        ▼         ▼                                           │
│  ┌────────────────────┐                                      │
│  │   fastapi_worker   │  (Celery)                            │
│  └────────────────────┘                                      │
│                                                              │
│  Volume: postgres_data (persistent)                          │
└──────────────────────────────────────────────────────────────┘
```

## 📚 API Documentation

### Authentication

All endpoints require an API Key in the header:

```bash
curl -H "x-api-key: test-api-key-123" http://localhost:8000/api/tasks/
```

### Endpoints

#### Health Check
```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### Create Task
```bash
POST /api/tasks/
Content-Type: application/json
x-api-key: test-api-key-123

{
  "name": "My Task",
  "description": "Task description"
}
```

**Response:**
```json
{
  "id": "a971d809-f425-4774-b81e-428a85529c79",
  "name": "My Task",
  "description": "Task description",
  "created_at": "2025-10-16T08:34:44.073934",
  "updated_at": "2025-10-16T08:34:44.073940"
}
```

**Note:** Creating a task automatically submits it to Celery for background processing.

#### List Tasks (with Pagination)
```bash
GET /api/tasks/?page=1&size=10
x-api-key: test-api-key-123
```

**Response:**
```json
{
  "items": [
    {
      "id": "a971d809-f425-4774-b81e-428a85529c79",
      "name": "My Task",
      "description": "Task description",
      "created_at": "2025-10-16T08:34:44.073934",
      "updated_at": "2025-10-16T08:34:44.073940"
    }
  ],
  "total": 25,
  "page": 1,
  "size": 10,
  "pages": 3
}
```

**Pagination Parameters:**
- `page` (default: 1) - Page number
- `size` (default: 50) - Items per page

#### Get Task by ID
```bash
GET /api/tasks/{task_id}
x-api-key: test-api-key-123
```

#### Update Task
```bash
PATCH /api/tasks/{task_id}
Content-Type: application/json
x-api-key: test-api-key-123

{
  "name": "Updated Task",
  "description": "New description"
}
```

**Note:** `updated_at` timestamp is automatically updated.

#### Delete Task
```bash
DELETE /api/tasks/{task_id}
x-api-key: test-api-key-123
```

**Response:** 204 No Content

### Full Example Workflow

```bash
# 1. Create a task
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/tasks/" \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-api-key-123" \
  -d '{"name": "Process Video", "description": "Convert to 720p"}')

# 2. Extract task ID
TASK_ID=$(echo $RESPONSE | grep -o '"id": *"[^"]*"' | cut -d'"' -f4)

# 3. Get task details
curl -H "x-api-key: test-api-key-123" \
  "http://localhost:8000/api/tasks/$TASK_ID"

# 4. Update task
curl -X PATCH "http://localhost:8000/api/tasks/$TASK_ID" \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-api-key-123" \
  -d '{"name": "Video Processed"}'

# 5. Verify Celery processed it
docker-compose logs worker | grep "succeeded"

# 6. Delete task
curl -X DELETE "http://localhost:8000/api/tasks/$TASK_ID" \
  -H "x-api-key: test-api-key-123"
```

## 💻 Development

### Local Setup (without Docker)

**Note:** Docker is recommended for most users. Only set up locally if you need to run without Docker.

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install pre-commit hooks (optional - for automatic git hooks)
poetry run pre-commit install

# Set up local services (PostgreSQL and Redis needed)
# Option 1: Use Docker for services only
docker-compose up -d db redis

# Option 2: Install PostgreSQL and Redis locally
# Update .env with local connection strings
# DATABASE_URL=postgresql://user:pass@localhost:5432/db
# CELERY_BROKER_URL=redis://localhost:6379/0

# Run API
poetry run uvicorn app.main:app --reload

# Run Celery worker (in another terminal)
poetry run celery -A app.worker.celery_app worker --loglevel=info
```

### Environment Variables

Create a `.env` file (see `.env.example`):

```bash
# Database
DATABASE_URL=postgresql://fastapi_user:fastapi_password@db:5432/fastapi_db

# API Security
API_KEY=your-api-key-change-in-production

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Environment
ENVIRONMENT=development
```

### Adding a New Model

1. **Create the model** (inherits from Base):
```python
# app/db/models.py
from sqlalchemy import Column, String, Float
from app.db.base import Base

class Product(Base):
    __tablename__ = "products"

    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
```

2. **Create schemas** (inherit from BaseSchema):
```python
# app/schemas/product.py
from pydantic import BaseModel, Field
from app.schemas.base import BaseSchema

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)

class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = Field(None, gt=0)

class ProductResponse(BaseSchema):
    name: str
    price: float
```

3. **Create routes**:
```python
# app/api/routes/products.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import models
from app.db.database import get_db
from app.schemas.product import ProductCreate, ProductResponse

router = APIRouter()

@router.post("/", response_model=ProductResponse)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    product = models.Product(**data.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
```

4. **Register router**:
```python
# app/main.py
from app.api.routes import products

app.include_router(
    products.router,
    prefix=f"{settings.API_V1_STR}/products",
    tags=["Products"]
)
```

### Creating Celery Tasks

```python
# app/worker/tasks.py
from app.worker.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3)
def process_video(self, video_id: str):
    """Process video asynchronously"""
    try:
        # Your processing logic here
        result = {"status": "success", "video_id": video_id}
        return result
    except Exception as e:
        # Retry on failure
        raise self.retry(exc=e, countdown=60)
```

**Usage in routes:**
```python
# Submit task (non-blocking)
task = process_video.apply_async(args=[video_id])

# Get task ID for tracking
task_id = task.id
```

## 🧪 Testing

### Run All Tests

```bash
# With Docker
docker-compose exec api pytest -v

# With coverage report
docker-compose exec api pytest --cov=app --cov-report=html

# View coverage report
# Open htmlcov/index.html in your browser

# Specific test file
docker-compose exec api pytest tests/api/test_example.py -v

# Specific test function
docker-compose exec api pytest tests/api/test_example.py::test_create_task -v
```

### Current Test Coverage

```
TOTAL: 160 statements, 20 missed
Coverage: 88%
```

### Test Structure

```
tests/
├── api/
│   └── test_example.py    # API endpoint tests
├── unit/
│   └── (add unit tests)   # Unit tests for services/utils
└── conftest.py            # Shared fixtures
```

### Writing Tests

```python
# tests/api/test_products.py
def test_create_product(client):
    """Test creating a product"""
    response = client.post(
        "/api/products/",
        json={"name": "Laptop", "price": 999.99},
        headers={"x-api-key": "test-api-key-123"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Laptop"
    assert "id" in data
    assert "created_at" in data
```

### Test Fixtures

Common fixtures are defined in `conftest.py`:

- `client` - TestClient for API testing
- `db` - Database session for testing

## 🔍 Code Quality

### Linters and Formatters

**Recommended: Run linters directly with Docker** (no git required):

```bash
# Format code with Black
docker-compose exec api black app/ tests/

# Sort imports
docker-compose exec api isort app/ tests/

# Check style
docker-compose exec api flake8 app/ tests/

# Type checking
docker-compose exec api mypy app/

# Run all checks at once
docker-compose exec api black app/ tests/ --check && \
  docker-compose exec api isort app/ tests/ --check-only && \
  docker-compose exec api flake8 app/ tests/ && \
  docker-compose exec api mypy app/
```

**Tools configured:**
- **Black** - Code formatter (line length: 100)
- **isort** - Import sorter
- **Flake8** - Style guide enforcement
- **mypy** - Static type checker

### Pre-commit Hooks (Optional - Local Development)

Pre-commit hooks run automatically before each commit. This requires **local Python setup** (not Docker):

```bash
# Install Poetry locally
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies locally
poetry install

# Install pre-commit hooks
poetry run pre-commit install

# Now hooks run automatically on git commit
# Or run manually:
poetry run pre-commit run --all-files
```

**Note:** Pre-commit hooks are optional. You can use the Docker linting commands above instead.

### Configuration Files

- `.pre-commit-config.yaml` - Pre-commit hooks
- `pyproject.toml` - Tool configurations (Black, pytest, mypy, isort)
- `.flake8` - Flake8 specific config

### Code Style Rules

- Line length: 100 characters
- Imports sorted by: stdlib → third-party → local
- Type hints required for public functions
- Docstrings for all public modules, classes, and functions

## 🐳 Docker Commands

### Container Management

```bash
# Start services in background
docker-compose up -d

# Start with rebuild
docker-compose up --build -d

# Stop services (keeps data)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (clean slate)
docker-compose down -v

# View logs
docker-compose logs -f          # All services
docker-compose logs -f api      # Specific service
docker-compose logs --tail=50 worker  # Last 50 lines

# Execute command in container
docker-compose exec api bash    # Open shell
docker-compose exec api python scripts/load_data.py

# View service status
docker-compose ps

# Restart specific service
docker-compose restart api
```

### Database Operations

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U fastapi_user -d fastapi_db

# Common SQL commands
\dt                    # List tables
\d tasks              # Describe table
SELECT * FROM tasks;  # Query data
\q                    # Quit

# Backup database
docker-compose exec db pg_dump -U fastapi_user fastapi_db > backup.sql

# Restore database
docker-compose exec -T db psql -U fastapi_user fastapi_db < backup.sql
```

### Redis Operations

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Common Redis commands
KEYS *                # List all keys
GET key_name          # Get value
DEL key_name          # Delete key
FLUSHALL              # Clear all data
INFO                  # Server info
exit                  # Quit
```

### Celery Operations

```bash
# View active tasks
docker-compose exec worker celery -A app.worker.celery_app inspect active

# View registered tasks
docker-compose exec worker celery -A app.worker.celery_app inspect registered

# View worker stats
docker-compose exec worker celery -A app.worker.celery_app inspect stats

# Purge all tasks from queue
docker-compose exec worker celery -A app.worker.celery_app purge
```

## 🚢 Deployment

### Scaling Workers

```bash
# Scale Celery workers horizontally
docker-compose up -d --scale worker=4

# Or update docker-compose.yml
services:
  worker:
    deploy:
      replicas: 4
```

## 📊 Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Database health
docker-compose exec db pg_isready -U fastapi_user

# Redis health
docker-compose exec redis redis-cli ping

# Worker health (check if processing tasks)
docker-compose logs --tail=10 worker
```

### Celery Monitoring

```bash
# View worker status
docker-compose exec worker celery -A app.worker.celery_app inspect active

# View registered tasks
docker-compose exec worker celery -A app.worker.celery_app inspect registered

# Monitor in real-time
docker-compose logs -f worker | grep "succeeded\|failed"
```
## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Celery](https://docs.celeryproject.org/)
- [Pydantic](https://docs.pydantic.dev/)
- [Poetry](https://python-poetry.org/)
- [Docker](https://www.docker.com/)

---

**Need help?** Check the [documentation](http://localhost:8000/docs) or open an issue.
