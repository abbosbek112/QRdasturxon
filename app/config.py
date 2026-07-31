from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    secret_key: str = "dev-insecure-secret-change-me"
    database_url: str = f"sqlite:///{BASE_DIR / 'qrdasturxon.db'}"
    base_url: str = "http://localhost:8000"
    media_dir: str = "media"
    debug: bool = True

    @property
    def media_path(self) -> Path:
        path = Path(self.media_dir)
        return path if path.is_absolute() else BASE_DIR / path


settings = Settings()
