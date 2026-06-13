from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import anyio

from .config import Settings
from .schemas import ContactRequest


logger = logging.getLogger(__name__)


def _format_optional(value: object) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def _build_message(settings: Settings, contact: ContactRequest, idx: int, pdgroup_name: str | None) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"S&S Incom quote request #{idx}"
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(settings.mail_recipients)
    message.set_content(
        "\n".join(
            [
                f"Contact request #{idx}",
                "",
                f"Name: {_format_optional(contact.person_name)}",
                f"Organization: {_format_optional(contact.org_name)}",
                f"Phone: {_format_optional(contact.tel)}",
                f"Email: {_format_optional(contact.email)}",
                f"Product group: {_format_optional(pdgroup_name)}",
                f"Required size: {_format_optional(contact.req_size)}",
                f"Delivery location: {_format_optional(contact.address_send)}",
                "",
                "Details:",
                _format_optional(contact.detail),
            ]
        )
    )
    return message


def _send_sync(settings: Settings, message: EmailMessage) -> None:
    if settings.smtp_use_tls:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)


async def send_contact_email(
    settings: Settings,
    contact: ContactRequest,
    idx: int,
    pdgroup_name: str | None,
) -> bool:
    if not settings.smtp_configured:
        logger.warning("SMTP is not configured; contact request %s was saved without email notification", idx)
        return False

    try:
        message = _build_message(settings, contact, idx, pdgroup_name)
        await anyio.to_thread.run_sync(_send_sync, settings, message)
        return True
    except Exception:
        logger.exception("Failed to send contact request email for idx=%s", idx)
        return False
