"""Application configuration"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Project
    PROJECT_NAME: str = "FastAPI Template"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    MAX_VIDEO_SIZE: int = 10 * 1024 * 1024  # 10 MB

    # File Storage
    # Storage backend: 'local' or 's3'
    STORAGE_BACKEND: str = "local"  # Default to local for development

    # Local storage paths (for local development)
    MEDIA_ROOT: str = "/app/media"
    UPLOAD_BASE_DIR: str = "/app/media/uploads"
    PROCESSED_BASE_DIR: str = "/app/media/processed"
    APP_BASE_DIR: str = "/app"  # Container/EC2 working directory

    # AWS S3 Configuration (uses IAM Role by default, no keys needed)
    AWS_S3_BUCKET: str = ""  # Set in production
    AWS_REGION: str = "us-east-1"
    S3_UPLOAD_PREFIX: str = "uploads/"
    S3_PROCESSED_PREFIX: str = "processed/"

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # SQS Configuration (Entrega 4 - replaces Celery/Redis)
    SQS_QUEUE_URL: str = ""  # Main processing queue URL
    SQS_DLQ_URL: str = ""  # Dead Letter Queue URL

    # JWT Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Environment
    ENVIRONMENT: str = "development"

    class Config:
        """Pydantic config"""

        env_file = ".env"
        case_sensitive = True


settings = Settings()  # type: ignore
