import html
import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class AmbitionMicEmailError(Exception):
    """Raised when Brevo cannot accept an Ambition Mic entry email."""


@dataclass(frozen=True)
class AmbitionMicEntry:
    full_name: str
    email: str
    phone_number: str
    city: str
    education_level: str
    institution_name: str


def _brevo_config() -> tuple[str, str, str, str]:
    api_key = settings.BREVO_API_KEY.strip()
    sender_name = settings.BREVO_FROM_NAME.strip() or "Ambition Mic Contest"
    sender_email = settings.BREVO_FROM_EMAIL.strip()
    recipient = settings.AMBITION_MIC_RECIPIENT.strip()

    if not api_key or not sender_email or not recipient:
        raise AmbitionMicEmailError("Brevo is not configured")
    return api_key, sender_name, sender_email, recipient


async def send_ambition_mic_entry(
    entry: AmbitionMicEntry,
    video_url: str,
) -> str:
    api_key, sender_name, sender_email, recipient = _brevo_config()
    url = f"{settings.BREVO_API_BASE_URL.rstrip('/')}/smtp/email"

    text_body = (
        "A new Ambition Mic contest entry has been submitted.\n\n"
        f"Full name: {entry.full_name}\n"
        f"Email address: {entry.email}\n"
        f"Phone number: {entry.phone_number}\n"
        f"City: {entry.city}\n"
        f"Current education level: {entry.education_level}\n"
        f"School / College / University: {entry.institution_name}\n\n"
        f"View / download video: {video_url}"
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
    escaped_video_url = html.escape(video_url, quote=True)
    html_body = (
        "<h2>New Ambition Mic contest entry</h2>"
        f"<table>{html_rows}</table>"
        "<h3 style='margin:24px 0 10px'>Submitted video</h3>"
        f"<p><a href=\"{escaped_video_url}\" target=\"_blank\" "
        "style='display:inline-block;padding:12px 18px;background:#0d6efd;"
        "color:#ffffff;text-decoration:none;border-radius:6px;font-weight:600'>"
        "View / download video</a></p>"
        "<p style='margin-top:16px;color:#555'>If the button does not work, copy and "
        "open this URL in your browser:</p>"
        f"<p style='word-break:break-all'><a href=\"{escaped_video_url}\" "
        f"target=\"_blank\">{escaped_video_url}</a></p>"
    )

    try:
        # Do not inherit an unrelated machine-level proxy for Mailgun delivery.
        async with httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"),
            timeout=httpx.Timeout(120.0),
            trust_env=False,
        ) as client:
            response = await client.post(
                url,
                headers={
                    "api-key": api_key,
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                json={
                    "sender": {"name": sender_name, "email": sender_email},
                    "to": [{"email": recipient}],
                    "replyTo": {"name": entry.full_name, "email": entry.email},
                    "subject": f"New Ambition Mic Entry - {entry.full_name}",
                    "textContent": text_body,
                    "htmlContent": html_body,
                },
            )
    except httpx.HTTPError as exc:
        logger.exception("Brevo request failed for Ambition Mic entry")
        raise AmbitionMicEmailError("Unable to contact the email service") from exc

    if response.status_code >= 400:
        logger.error(
            "Brevo rejected Ambition Mic entry email: status=%s response=%s",
            response.status_code,
            response.text[:500],
        )
        raise AmbitionMicEmailError("The email service rejected the submission")

    try:
        return response.json().get("messageId", "")
    except ValueError:
        return ""
