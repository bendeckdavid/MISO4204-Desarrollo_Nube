"""Application configuration"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Project
    PROJECT_NAME: str = "FastAPI Template"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    MAX_VIDEO_SIZE: int = 10 * 1024 * 1024  # 10 MB

    # File Storage (Container-aware paths)
    UPLOAD_BASE_DIR: str = "/app/videos/uploads"
    PROCESSED_BASE_DIR: str = "/app/videos/processed"
    APP_BASE_DIR: str = "/app"  # Container working directory

    # Database
    DATABASE_URL: str

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

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
