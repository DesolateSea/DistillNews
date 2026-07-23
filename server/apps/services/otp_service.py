import os
import uuid
import json
import random
import logging
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from redis.asyncio import Redis
from apps.core.config import REDIS_URL

logger = logging.getLogger(__name__)

# Initialize Redis client using connection URL
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)


def generate_otp() -> str:
    """Generate a random 6-digit OTP."""
    return "".join(random.choices("0123456789", k=6))


def generate_session_token() -> str:
    """Generate a cryptographically random session token."""
    return uuid.uuid4().hex


async def store_otp(email: str, otp: str, expire_seconds: int = 300) -> str | None:
    """
    Store OTP + email keyed by a new session token in Redis.
    Returns the session_token on success, None on failure.
    """
    try:
        session_token = generate_session_token()
        key = f"otp_session:{session_token}"
        payload = json.dumps({"email": email, "otp": otp})
        await redis_client.set(key, payload, ex=expire_seconds)
        logger.info(f"OTP stored for {email} under session {session_token[:8]}…")
        return session_token
    except Exception as e:
        logger.error(f"Failed to store OTP in Redis: {e}")
        return None


async def verify_otp(email: str, otp_to_verify: str, session_token: str) -> bool:
    """
    Verify the OTP by looking up the session token.
    Deletes the key on success to prevent reuse.
    """
    try:
        key = f"otp_session:{session_token}"
        raw = await redis_client.get(key)
        if not raw:
            logger.warning(f"No OTP session found for token {session_token[:8]}…")
            return False

        data = json.loads(raw)
        if data.get("email") != email:
            logger.warning(f"Email mismatch for session {session_token[:8]}…")
            return False
        if data.get("otp") != otp_to_verify:
            logger.warning(f"OTP mismatch for session {session_token[:8]}…")
            return False

        await redis_client.delete(key)
        logger.info(f"OTP verified successfully for {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to verify OTP: {e}")
        return False


def _build_otp_html(otp: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;
                border: 1px solid #ddd; border-radius: 8px;">
        <h2 style="color: #333; text-align: center;">Verify Your Email</h2>
        <p>Hello,</p>
        <p>Your one-time password (OTP) for DistillNews is:</p>
        <div style="font-size: 32px; font-weight: bold; letter-spacing: 5px; text-align: center;
                    margin: 30px 0; color: #007bff;">
            {otp}
        </div>
        <p>This OTP is valid for 5 minutes. Please do not share this code with anyone.</p>
        <p>Best regards,<br/>The DistillNews Team</p>
    </div>
    """


def _send_smtp(to_email: str, otp: str) -> None:
    """Synchronous SMTP send — runs in a thread via asyncio.to_thread."""
    sender = os.environ.get("EMAIL")
    password = os.environ.get("PASS")

    logger.info(f"SMTP sender resolved: {sender!r}")

    if not sender or not password:
        raise ValueError(
            f"EMAIL or PASS environment variable is not set. EMAIL={sender!r}"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🔑 Your OTP Verification Code"
    msg["From"] = sender
    msg["To"] = to_email
    msg.attach(MIMEText(_build_otp_html(otp), "html"))

    # Try port 587 (STARTTLS) first, fall back to port 465 (SSL)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
            logger.info(f"OTP email sent via port 587 to {to_email}")
            return
    except Exception as e587:
        logger.warning(f"Port 587 failed ({e587}), trying port 465 …")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
        server.ehlo()
        server.login(sender, password)
        server.sendmail(sender, to_email, msg.as_string())
        logger.info(f"OTP email sent via port 465 to {to_email}")


async def send_otp_email(email: str, otp: str) -> bool:
    """Send an OTP email using Python smtplib (no subprocess)."""
    try:
        await asyncio.to_thread(_send_smtp, email, otp)
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        return False
