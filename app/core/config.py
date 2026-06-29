from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "PDF Converter API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    DATABASE_URL: str = "postgresql+asyncpg://pdfuser:pdfpassword@localhost:5432/pdfconverter"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://pdfuser:pdfpassword@localhost:5432/pdfconverter"
    REDIS_URL: str = "redis://localhost:6379/0"

    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
settings.UPLOAD_DIR.mkdir(exist_ok=True)
settings.OUTPUT_DIR.mkdir(exist_ok=True)
