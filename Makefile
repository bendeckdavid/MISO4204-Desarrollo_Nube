.PHONY: help install dev test lint format clean docker-up docker-down load-data

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with Poetry
	poetry install

dev: ## Run development server
	poetry run uvicorn app.main:app --reload

worker: ## Run Celery worker
	poetry run celery -A app.worker.celery_app worker --loglevel=info

test: ## Run tests with coverage
	poetry run pytest -v --cov=app --cov-report=html --cov-report=term

test-quick: ## Run tests without coverage
	poetry run pytest -v

lint: ## Run all linters
	poetry run black app tests --check
	poetry run isort app tests --check
	poetry run flake8 app tests
	poetry run mypy app

format: ## Format code with black and isort
	poetry run black app tests
	poetry run isort app tests

pre-commit: ## Install pre-commit hooks
	pre-commit install

pre-commit-run: ## Run pre-commit on all files
	pre-commit run --all-files

docker-up: ## Start Docker containers
	docker-compose up --build

docker-down: ## Stop Docker containers
	docker-compose down

docker-clean: ## Stop containers and remove volumes
	docker-compose down -v

load-data: ## Load test data into database
	poetry run python scripts/load_test_data.py

docker-load-data: ## Load test data in Docker environment
	docker-compose exec api python scripts/load_test_data.py

docker-logs: ## Show Docker logs
	docker-compose logs -f

docker-test: ## Run tests in Docker
	docker-compose exec api pytest -v

clean: ## Clean temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	find . -type f -name "test.db" -delete

sonar: ## Run SonarQube analysis
	sonar-scanner
