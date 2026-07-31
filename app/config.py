from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

INSECURE_SECRET = "dev-insecure-secret-change-me"
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    secret_key: str = INSECURE_SECRET
    database_url: str = f"sqlite:///{BASE_DIR / 'qrdasturxon.db'}"
    base_url: str = "http://localhost:8000"
    media_dir: str = "media"
    # Xavfsiz tomonga qaratilgan standart: .env unutilsa ham prod rejimida qoladi
    debug: bool = False
    # Sessiya cookie'si shuncha vaqtdan keyin kuchini yo'qotadi
    session_max_age: int = 60 * 60 * 24 * 14

    # Reklama sahifasida ko'rsatiladigan aloqa — kodga tegmasdan o'zgartirish uchun
    contact_phone: str = "+998 94 227 34 07"
    contact_telegram: str = "odam_dev"

    @property
    def contact_phone_href(self) -> str:
        """tel: havolasi uchun faqat raqamlar va bosh + belgisi."""
        digits = "".join(ch for ch in self.contact_phone if ch.isdigit())
        return f"+{digits}"

    @property
    def media_path(self) -> Path:
        path = Path(self.media_dir)
        return path if path.is_absolute() else BASE_DIR / path

    @model_validator(mode="after")
    def _reject_insecure_secret(self) -> "Settings":
        """Prod rejimida zaif kalit bilan ishga tushishga yo'l qo'ymaydi.

        Kalit sessiyani imzolaydi. U ma'lum yoki qisqa bo'lsa, birov o'zini
        admin qilib ko'rsatuvchi cookie yasab kira oladi — shuning uchun bu
        yerda ogohlantirish emas, to'xtatish kerak.
        """
        if self.debug:
            return self
        if self.secret_key == INSECURE_SECRET:
            raise ValueError(
                "SECRET_KEY standart qiymatda qolgan. .env faylida o'zgartiring:\n"
                '  python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        if len(self.secret_key) < MIN_SECRET_LENGTH:
            raise ValueError(
                f"SECRET_KEY juda qisqa ({len(self.secret_key)} belgi). "
                f"Kamida {MIN_SECRET_LENGTH} belgi bo'lsin."
            )
        return self


settings = Settings()
