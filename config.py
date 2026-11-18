import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN", "")
    TELEGRAM_GROUP_ID: Optional[str] = os.getenv("TELEGRAM_GROUP_ID", "")
    TELEGRAM_CHANNEL_URL: Optional[str] = os.getenv("TELEGRAM_CHANNEL_URL", "https://t.me")
    TELEGRAM_PROXY: Optional[str] = os.getenv("TELEGRAM_PROXY", "")
    
    META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "joylinks_target_verify_2026")
    META_PAGE_ACCESS_TOKEN: Optional[str] = os.getenv("META_PAGE_ACCESS_TOKEN", "")
    META_PIXEL_ID: Optional[str] = os.getenv("META_PIXEL_ID", "")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./crm_joylink.db")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    CENTER_NAME: str = os.getenv("CENTER_NAME", "Joylinks IT Akademiyasi")

settings = Settings()
