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

    # Afitsant ilovasi. Ikkalasi ham do'kon ro'yxatisiz tarqatiladi:
    # Android — saytdan APK, iPhone — TestFlight havolasi.
    #
    # TestFlight havolasi bo'sh bo'lsa /ilova sahifasi iPhone egasiga PWA
    # yo'riqnomasini ko'rsatadi — ya'ni sahifa hech qachon bo'sh qolmaydi.
    app_version: str = "1.0.0"
    testflight_url: str = ""

    # Afitsant bildirishnomasi (Web Push) uchun VAPID kalitlari.
    #
    # Maxfiy kalit SERVERDA yasaladi va faqat o'sha yerda yashaydi —
    # SECRET_KEY bilan bir xil tartib:
    #   python -m scripts.vapid_keys
    #
    # Bo'sh qolsa bildirishnoma jimgina o'chiq bo'ladi va qolgan hamma narsa
    # avvalgidek ishlayveradi. Bu ataylab: kalit unutilgani sababli buyurtma
    # qabul qilinmay qolishi mumkin emas.
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    # Push serveri muammo chiqsa shu manzilga yozadi. mailto: yoki https:
    vapid_subject: str = "mailto:azizovabbos61@gmail.com"

    @property
    def push_enabled(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key)

    # Vaqt bazada UTC saqlanadi, ekranda esa mahalliy vaqt ko'rinishi kerak.
    # O'zbekiston UTC+5 va yozgi vaqtga o'tmaydi, shuning uchun oddiy siljish
    # yetarli. Buyurtmalar uchun bu muhim: afitsant "06:14" ni ko'rib, soatiga
    # qarasa 11:14 turgan bo'lardi.
    utc_offset_hours: int = 5

    # Reklama sahifasida ko'rsatiladigan aloqa — kodga tegmasdan o'zgartirish uchun
    contact_phone: str = "+998 94 227 34 07"
    contact_telegram: str = "odam_dev"

    # "Namunani ko'rish" qaysi menyuni ochadi. Aniq ko'rsatilmasa eng eski
    # restoran tanlanardi — ya'ni haqiqiy mijozning menyusi namuna bo'lib
    # qolardi. scripts/seed_demo.py shu slug bilan restoran quradi.
    demo_slug: str = "bodom"

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
