from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production-please-use-env-variable"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24        # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database - Use SQLite for local development, PostgreSQL for production
    DATABASE_URL: str = "sqlite+aiosqlite:///./recovery_companion.db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 2

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AWS
    AWS_REGION: str = "ap-south-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_FOOD_IMAGES: str = "rc-food-images"
    S3_BUCKET_PRESCRIPTIONS: str = "rc-prescriptions"

    # AI / LLM
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""           # fallback for STT

    # Google Cloud (STT + Vision)
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    GOOGLE_PROJECT_ID: str = ""

    # Firebase (FCM push)
    FIREBASE_CREDENTIALS_PATH: str = ""

    # DrugBank (interaction DB)
    DRUGBANK_API_KEY: str = ""
    DRUGBANK_BASE_URL: str = "https://api.drugbank.com/v1"

    # CORS - using str, will be split in property
    ALLOWED_ORIGINS: str = "http://localhost:3000,https://clinician.recoverycompanion.app"
    ALLOWED_HOSTS: str = "api.recoverycompanion.app"

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated origins into list."""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        return self.ALLOWED_ORIGINS

    @property
    def cors_hosts(self) -> List[str]:
        """Parse comma-separated hosts into list."""
        if isinstance(self.ALLOWED_HOSTS, str):
            return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]
        return self.ALLOWED_HOSTS

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
