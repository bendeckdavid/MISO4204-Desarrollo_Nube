# FastAPI Template - ANB Rising Stars Showcase API

A production-ready FastAPI template with JWT Authentication, PostgreSQL, Celery, Redis, and Docker. Built for the ANB Rising Stars Showcase project.

## 🚀 Features

- ✅ **FastAPI** - Modern, fast web framework for building APIs
- ✅ **JWT Authentication** - Secure token-based authentication with bcrypt password hashing
- ✅ **PostgreSQL** - Reliable relational database with UUID primary keys
- ✅ **SQLAlchemy 2.0** - ORM with hybrid properties for password management
- ✅ **Celery + Redis** - Distributed task queue for background processing
- ✅ **Docker Compose** - Multi-container orchestration
- ✅ **Pydantic v2** - Data validation with environment-based configuration
- ✅ **Poetry** - Modern dependency management
- ✅ **pytest** - Comprehensive test suite with 87% coverage
- ✅ **CI/CD Pipeline** - Automated testing, linting, and Docker builds with GitHub Actions
- ✅ **Code Quality Tools** - flake8, black, mypy, isort

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Authentication](#-authentication)
- [API Documentation](#-api-documentation)
- [Testing the API](#-testing-the-api)
- [Development](#-development)
- [Code Quality](#-code-quality)
- [CI/CD Pipeline](#-cicd-pipeline)
- [Docker Commands](#-docker-commands)

## 🏃 Quick Start

### Prerequisites

- Docker >= 20.10
- Docker Compose >= 2.0
- Python 3.13+ (for local development)

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd MISO4204-Desarrollo_Nube

# The .env file is already configured for development
# You can modify it if needed
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
fastapi_api      uvicorn app.main:app --hos ...   Up             0.0.0.0:8000->8000/tcp
fastapi_db       docker-entrypoint.sh postgres    Up (healthy)   0.0.0.0:5433->5432/tcp
fastapi_redis    docker-entrypoint.sh redis ...   Up (healthy)   0.0.0.0:6380->6379/tcp
fastapi_worker   celery -A app.worker.celer ...   Up             8000/tcp
```

### 3. Verify Installation

```bash
# Check health
curl http://localhost:8000/health
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
│   │       ├── auth.py             # Authentication (signup, login)
│   │       └── videos.py           # Video upload endpoint
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Settings (Pydantic, env variables)
│   │   └── security.py             # JWT token management
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base model (UUID, timestamps)
│   │   ├── database.py             # SQLAlchemy setup
│   │   └── models.py               # Database models (User, Task)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Auth schemas (Signup, Login, Token)
│   │   └── video.py                # Video schemas (Upload, Response)
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── celery_app.py           # Celery configuration
│   │   └── tasks.py                # Async tasks
│   └── main.py                     # FastAPI application entry point
├── tests/
│   └── conftest.py                 # Test fixtures
├── scripts/
│   └── load_data.py                # Sample data loader
├── .env                            # Environment variables
├── .pre-commit-config.yaml         # Pre-commit hooks config
├── docker-compose.yml              # Docker services orchestration
├── Dockerfile                      # API & Worker image
├── pyproject.toml                  # Poetry dependencies & config
└── README.md                       # This file
```

### Key Components

#### User Model with Password Hashing (`app/db/models.py`)

The User model includes automatic password hashing using bcrypt:

```python
class User(Base):
    __tablename__ = "users"

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    _password = Column("password", String(255), nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, plaintext_password: str):
        """Hash password using bcrypt when setting it."""
        self._password = bcrypt.hashpw(
            plaintext_password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    def verify_password(self, plaintext_password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return bcrypt.checkpw(
            plaintext_password.encode("utf-8"),
            self._password.encode("utf-8")
        )
```

**Key features:**
- ✅ Passwords are automatically hashed when assigned
- ✅ Direct password verification method on the model
- ✅ Stored in `password` column (not `password_hash`)
- ✅ Uses bcrypt for secure hashing

## 🔐 Authentication

### JWT Token-Based Authentication

The API uses JWT (JSON Web Tokens) for authentication:

1. **Signup** - Create a new user account
2. **Login** - Get a JWT token
3. **Protected Endpoints** - Use the token in the `Authorization` header

### Environment Configuration

JWT settings are configurable via environment variables in `.env`:

```bash
# JWT Configuration
SECRET_KEY=your-secret-key-change-this-in-production-use-openssl-rand-hex-32
ACCESS_TOKEN_EXPIRE_MINUTES=60  # Token expiration in minutes
```

**Configuration options:**
- `SECRET_KEY` - Secret key for JWT signing (change in production!)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration time (default: 60 minutes)


## 📚 API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints Overview

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/health` | GET | No | Health check |
| `/api/auth/signup` | POST | No | Register new user |
| `/api/auth/login` | POST | No | Login and get JWT token |
| `/api/videos/upload` | POST | Yes (JWT) | Upload video |

---

### 1️⃣ Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API is running

**Request:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

### 2️⃣ User Signup

**Endpoint:** `POST /api/auth/signup`

**Description:** Register a new user account

**Request:**
```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Juan",
    "last_name": "Pérez",
    "email": "juan@example.com",
    "password1": "securepassword123",
    "password2": "securepassword123",
    "city": "Bogotá",
    "country": "Colombia"
  }'
```

**Request Body:**
```json
{
  "first_name": "string",      // Required, max 100 chars
  "last_name": "string",       // Required, max 100 chars
  "email": "string",           // Required, valid email, unique
  "password1": "string",       // Required, min 8 chars
  "password2": "string",       // Required, must match password1
  "city": "string",            // Required, max 100 chars
  "country": "string"          // Required, max 100 chars
}
```

**Response (201 Created):**
```json
{
  "message": "User created successfully",
  "user_id": "c8b44023-1172-4a56-b440-045120713d14"
}
```

**Error Responses:**
- **400 Bad Request** - Email already registered or passwords don't match
- **422 Unprocessable Entity** - Validation error (invalid email, short password, etc.)

---

### 3️⃣ User Login

**Endpoint:** `POST /api/auth/login`

**Description:** Authenticate and receive a JWT token

**Request:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "juan@example.com",
    "password": "securepassword123"
  }'
```

**Request Body:**
```json
{
  "email": "string",      // Required
  "password": "string"    // Required
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjOGI0NDAyMy0xMTcyLTRhNTYtYjQ0MC0wNDUxMjA3MTNkMTQiLCJleHAiOjE3NjA3NzkyODN9.p6RBMfqwqQvfhzd8NkGXM36UiZ7Gch2A0_HGhFvaLXM",
  "token_type": "Bearer",
  "expires_in": 3600  // Seconds (60 minutes * 60)
}
```

**Token Details:**
- **Type:** JWT (JSON Web Token)
- **Expiration:** Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 1 hour)
- **Contains:** User ID in the `sub` claim

**Error Responses:**
- **401 Unauthorized** - Invalid email or password

**Save the token for protected endpoints!**

---

### 4️⃣ Upload Video

**Endpoint:** `POST /api/videos/upload`

**Description:** Upload a video (protected endpoint)

**Authentication:** Required (JWT token)

**Request:**
```bash
curl -X POST http://localhost:8000/api/videos/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "test": "Mi video de habilidades"
  }'
```

**Request Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "test": "string"  // Required
}
```

**Response (201 Created):**
```json
{
  "id": "example-video-id",
  "user_id": "c8b44023-1172-4a56-b440-045120713d14"
}
```

**Error Responses:**
- **401 Unauthorized** - Missing or invalid JWT token
- **422 Unprocessable Entity** - Validation error

---

## 🧪 Testing the API

### Complete Test Script

Save this as `test_api.sh`:

```bash
#!/bin/bash

echo "=========================================="
echo "  ANB Rising Stars API - Complete Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost:8000"

echo "${BLUE}=== 1. Health Check ===${NC}"
curl -s $BASE_URL/health | python3 -m json.tool
echo -e "\n"

echo "${BLUE}=== 2. User Signup ===${NC}"
SIGNUP_RESPONSE=$(curl -s -X POST $BASE_URL/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "email": "testuser@example.com",
    "password1": "testpass123",
    "password2": "testpass123",
    "city": "Medellín",
    "country": "Colombia"
  }')

echo $SIGNUP_RESPONSE | python3 -m json.tool

# Check if signup was successful
if echo $SIGNUP_RESPONSE | grep -q "user_id"; then
    echo -e "${GREEN}✓ Signup successful${NC}"
else
    echo -e "${RED}✗ Signup failed (user might already exist)${NC}"
fi
echo ""

echo "${BLUE}=== 3. User Login ===${NC}"
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "testpass123"
  }')

echo $LOGIN_RESPONSE | python3 -m json.tool

# Extract token
TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Login failed - could not get token${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Login successful${NC}"
    echo -e "${BLUE}Token (first 50 chars): ${TOKEN:0:50}...${NC}"
fi
echo ""

echo "${BLUE}=== 4. Upload Video (WITH token) ===${NC}"
UPLOAD_RESPONSE=$(curl -s -X POST $BASE_URL/api/videos/upload \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test": "Mi video de habilidades increíbles"
  }')

echo $UPLOAD_RESPONSE | python3 -m json.tool

if echo $UPLOAD_RESPONSE | grep -q "id"; then
    echo -e "${GREEN}✓ Video upload successful${NC}"
else
    echo -e "${RED}✗ Video upload failed${NC}"
fi
echo ""

echo "${BLUE}=== 5. Upload Video (WITHOUT token - should fail) ===${NC}"
FAIL_RESPONSE=$(curl -s -X POST $BASE_URL/api/videos/upload \
  -H "Content-Type: application/json" \
  -d '{
    "test": "This should fail"
  }')

echo $FAIL_RESPONSE | python3 -m json.tool

if echo $FAIL_RESPONSE | grep -q "Not authenticated"; then
    echo -e "${GREEN}✓ Authentication working correctly (request blocked)${NC}"
else
    echo -e "${RED}✗ Authentication not working${NC}"
fi
echo ""

echo "${GREEN}=========================================="
echo "  All tests completed!"
echo "==========================================${NC}"
```

Make it executable and run:
```bash
chmod +x test_api.sh
./test_api.sh
```

### Manual Testing Steps

#### Step 1: Create a User
```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Juan",
    "last_name": "Pérez",
    "email": "juan@example.com",
    "password1": "mypassword123",
    "password2": "mypassword123",
    "city": "Bogotá",
    "country": "Colombia"
  }'
```

#### Step 2: Login and Get Token
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "juan@example.com",
    "password": "mypassword123"
  }'
```

**Save the `access_token` from the response!**

#### Step 3: Use Token for Protected Endpoint
```bash
# Export token as environment variable
export TOKEN="your_access_token_here"

# Upload video with authentication
curl -X POST http://localhost:8000/api/videos/upload \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test": "My amazing basketball skills"
  }'
```

#### Step 4: Test Without Token (Should Fail)
```bash
curl -X POST http://localhost:8000/api/videos/upload \
  -H "Content-Type: application/json" \
  -d '{
    "test": "This should fail"
  }'
```

**Expected response:**
```json
{
  "detail": "Not authenticated"
}
```

### Using Swagger UI (Interactive Testing)

1. Go to http://localhost:8000/docs
2. Click on **POST /api/auth/login**
3. Click **"Try it out"**
4. Enter credentials and execute
5. Copy the `access_token` from the response
6. Click the **"Authorize"** button at the top
7. Paste the token in the format: `Bearer <your_token>`
8. Click **"Authorize"**
9. Now you can test protected endpoints!

### Verify Database

Check users created in the database:
```bash
docker-compose exec db psql -U fastapi_user -d fastapi_db -c "SELECT id, email, first_name, last_name, city, country, created_at FROM users;"
```

## 💻 Development

### Environment Variables

The `.env` file contains all configuration:

```bash
# Database
DATABASE_URL=postgresql://fastapi_user:fastapi_password@db:5432/fastapi_db

# JWT Configuration (change in production!)
SECRET_KEY=your-secret-key-change-this-in-production-use-openssl-rand-hex-32
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Environment
ENVIRONMENT=development
```

**Important Configuration:**
- **SECRET_KEY** - Use `openssl rand -hex 32` to generate a secure key for production
- **ACCESS_TOKEN_EXPIRE_MINUTES** - Adjust based on security requirements
  - Development: 120+ minutes (convenience)
  - Production: 15-30 minutes (security)

### Local Setup (without Docker)

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install pre-commit hooks (optional)
poetry run pre-commit install

# Start services (PostgreSQL and Redis needed)
docker-compose up -d db redis

# Run API
poetry run uvicorn app.main:app --reload

# Run Celery worker (in another terminal)
poetry run celery -A app.worker.celery_app worker --loglevel=info
```

## 🔍 Code Quality

### Linters and Formatters

Run linters with Docker (recommended):

```bash
# Format code with Black
docker-compose exec api poetry run black .

# Sort imports
docker-compose exec api poetry run isort .

# Lint with flake8
docker-compose exec api poetry run flake8 app tests

# Type checking
docker-compose exec api poetry run mypy app

# Run all checks at once
docker-compose exec api poetry run black . --check && \
  docker-compose exec api poetry run flake8 app tests && \
  docker-compose exec api poetry run mypy app
```

**Tools configured:**
- **Black** - Code formatter (line length: 100)
- **isort** - Import sorter
- **flake8** - Python linter (PEP 8 compliance)
- **mypy** - Static type checker

### Running Tests

```bash
# Run all tests
docker-compose exec api poetry run pytest

# Run with coverage
docker-compose exec api poetry run pytest --cov=app --cov-report=term --cov-report=html

# Run specific test file
docker-compose exec api poetry run pytest tests/api/test_auth.py -v

# Run tests and open coverage report
docker-compose exec api poetry run pytest --cov=app --cov-report=html
# Then open htmlcov/index.html in your browser
```

### Pre-commit Hooks (Optional)

For local development with git hooks:

```bash
# Install pre-commit hooks (requires local Poetry setup)
docker-compose exec api poetry run pre-commit install

# Run manually
docker-compose exec api poetry run pre-commit run --all-files
```

## 🔄 CI/CD Pipeline

This project includes a GitHub Actions workflow that automatically runs on every push and pull request to `main` or `develop` branches.

### Pipeline Stages

**Stage 1: Tests and Linting**
- ✅ Sets up Python 3.13 and Poetry
- ✅ Caches dependencies for faster builds
- ✅ Runs linting with flake8
- ✅ Checks code formatting with black
- ✅ Performs type checking with mypy
- ✅ Executes all pytest tests with coverage
- ✅ Uploads coverage reports as artifacts

**Stage 2: Docker Build**
- ✅ Builds Docker image
- ✅ Validates Docker Compose configuration
- ✅ Uses build cache for optimization
- ✅ Only runs if tests pass

### Viewing Results

After pushing code to GitHub:

1. Go to your repository on GitHub
2. Click on the **"Actions"** tab
3. Select the latest workflow run
4. View the results of each job
5. Download coverage reports from the artifacts section

### Pipeline Configuration

The pipeline is defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) and includes:

- **Services:** PostgreSQL 16, Redis 7
- **Python Version:** 3.13
- **Tools:** Poetry, pytest, flake8, black, mypy
- **Coverage:** XML and HTML reports generated
- **Caching:** Dependencies and Docker layers cached for speed

## 🐳 Docker Commands

### Container Management

```bash
# Start services
docker-compose up -d

# Start with rebuild
docker-compose up --build -d

# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove everything (including volumes)
docker-compose down -v

# View logs
docker-compose logs -f api      # API logs
docker-compose logs -f worker   # Worker logs
docker-compose logs --tail=50 api  # Last 50 lines

# Execute commands
docker-compose exec api bash    # Open shell
docker-compose exec api python scripts/load_data.py

# Restart services
docker-compose restart api worker
```

### Database Operations

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U fastapi_user -d fastapi_db

# View users table
docker-compose exec db psql -U fastapi_user -d fastapi_db -c "SELECT * FROM users;"

# Backup database
docker-compose exec db pg_dump -U fastapi_user fastapi_db > backup.sql

# Restore database
docker-compose exec -T db psql -U fastapi_user fastapi_db < backup.sql
```

### Celery Operations

```bash
# View active tasks
docker-compose exec worker celery -A app.worker.celery_app inspect active

# View registered tasks
docker-compose exec worker celery -A app.worker.celery_app inspect registered

# Purge all tasks from queue
docker-compose exec worker celery -A app.worker.celery_app purge
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

**Need help?** Check the [interactive documentation](http://localhost:8000/docs) or review the code.
