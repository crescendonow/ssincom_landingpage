from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_password: str | None
    smtp_from: str
    smtp_use_tls: bool
    mail_recipients: tuple[str, ...]
    bill_base_url: str
    app_user: str
    app_pass: str
    session_secret: str

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    recipients = tuple(
        item.strip()
        for item in os.getenv(
            "CONTACT_MAIL_RECIPIENTS",
            "contact@ssincom.com,mailtossincom@gmail.com",
        ).split(",")
        if item.strip()
    )
    return Settings(
        database_url=os.getenv("DATABASE_URL", ""),
        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        smtp_from=os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "noreply@ssincom.com")),
        smtp_use_tls=_env_bool("SMTP_USE_TLS", True),
        mail_recipients=recipients,
        bill_base_url=os.getenv("BILL_BASE_URL", "https://ssincombill-production.up.railway.app"),
        app_user=os.getenv("APP_USER", "admin"),
        app_pass=os.getenv("APP_PASS", "change-me"),
        session_secret=os.getenv("SESSION_SECRET", "change-me-long-random-secret"),
    )
