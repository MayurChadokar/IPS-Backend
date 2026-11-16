import html
import logging
from dataclasses import dataclass
from typing import BinaryIO

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class AmbitionMicEmailError(Exception):
    """Raised when Mailgun cannot accept an Ambition Mic entry email."""


@dataclass(frozen=True)
class AmbitionMicEntry:
    full_name: str
    email: str
    phone_number: str
    city: str
    education_level: str
    institution_name: str


def _mailgun_config() -> tuple[str, str, str, str]:
    domain = settings.MAILGUN_DOMAIN.strip()
    api_key = settings.MAILGUN_API_KEY.strip()
    sender = settings.MAILGUN_FROM_EMAIL.strip() or (
        f"Ambition Mic Contest <postmaster@{domain}>" if domain else ""
    )
    recipient = settings.AMBITION_MIC_RECIPIENT.strip()

    if not domain or not api_key or not sender or not recipient:
        raise AmbitionMicEmailError("Mailgun is not configured")
    return domain, api_key, sender, recipient


async def send_ambition_mic_entry(
    entry: AmbitionMicEntry,
    video_file: BinaryIO,
    video_filename: str,
    video_content_type: str,
) -> str:
    domain, api_key, sender, recipient = _mailgun_config()
    api_base = settings.MAILGUN_API_BASE_URL.rstrip("/")
    url = f"{api_base}/v3/{domain}/messages"

    text_body = (
        "A new Ambition Mic contest entry has been submitted.\n\n"
        f"Full name: {entry.full_name}\n"
        f"Email address: {entry.email}\n"
        f"Phone number: {entry.phone_number}\n"
        f"City: {entry.city}\n"
        f"Current education level: {entry.education_level}\n"
        f"School / College / University: {entry.institution_name}\n\n"
        "The participant's video is attached to this email."
    )
    rows = (
        ("Full name", entry.full_name),
        ("Email address", entry.email),
        ("Phone number", entry.phone_number),
        ("City", entry.city),
        ("Current education level", entry.education_level),
        ("School / College / University", entry.institution_name),
    )
    html_rows = "".join(
        f"<tr><th style='text-align:left;padding:6px 12px 6px 0'>{html.escape(label)}</th>"
        f"<td style='padding:6px 0'>{html.escape(value)}</td></tr>"
        for label, value in rows
    )
    html_body = (
        "<h2>New Ambition Mic contest entry</h2>"
        f"<table>{html_rows}</table>"
        "<p>The participant's video is attached to this email.</p>"
    )

    try:
        video_file.seek(0)
        # Do not inherit an unrelated machine-level proxy for Mailgun delivery.
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            trust_env=False,
        ) as client:
            response = await client.post(
                url,
                auth=("api", api_key),
                data={
                    "from": sender,
                    "to": recipient,
                    "subject": f"New Ambition Mic Entry — {entry.full_name}",
                    "text": text_body,
                    "html": html_body,
                },
                files={
                    "attachment": (
                        video_filename,
                        video_file,
                        video_content_type or "application/octet-stream",
                    )
                },
            )
    except httpx.HTTPError as exc:
        logger.exception("Mailgun request failed for Ambition Mic entry")
        raise AmbitionMicEmailError("Unable to contact the email service") from exc

    if response.status_code >= 400:
        logger.error(
            "Mailgun rejected Ambition Mic entry email: status=%s response=%s",
            response.status_code,
            response.text[:500],
        )
        raise AmbitionMicEmailError("The email service rejected the submission")

    try:
        return response.json().get("id", "")
    except ValueError:
        return ""
