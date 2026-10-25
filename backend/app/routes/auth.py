
import base64
import hashlib
import hmac
import os
import time

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/auth", tags=["Admin Authentication"])

ADMIN_EMAIL = os.getenv("STUFEED_ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.getenv("STUFEED_ADMIN_PASSWORD", "")
SESSION_SECRET = os.getenv("STUFEED_SESSION_SECRET", "")
SESSION_DURATION_SECONDS = 8 * 60 * 60


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


def _configuration_is_valid() -> bool:
    return bool(ADMIN_EMAIL and ADMIN_PASSWORD and len(SESSION_SECRET) >= 32)


def _sign(value: str) -> str:
    digest = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def create_session_token(email: str) -> str:
    expires_at = int(time.time()) + SESSION_DURATION_SECONDS
    payload = f"{email.lower()}|{expires_at}"
    encoded_payload = base64.urlsafe_b64encode(
        payload.encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{_sign(encoded_payload)}"


def verify_session_token(token: str) -> bool:
    if not _configuration_is_valid():
        return False

    try:
        encoded_payload, supplied_signature = token.split(".", 1)
        expected_signature = _sign(encoded_payload)

        if not hmac.compare_digest(supplied_signature, expected_signature):
            return False

        padding = "=" * (-len(encoded_payload) % 4)
        payload = base64.urlsafe_b64decode(
            encoded_payload + padding
        ).decode("utf-8")

        email, expires_at_text = payload.rsplit("|", 1)
        expires_at = int(expires_at_text)

        return (
            hmac.compare_digest(email, ADMIN_EMAIL)
            and int(time.time()) < expires_at
        )
    except (ValueError, TypeError, UnicodeDecodeError):
        return False


@router.post("/login")
def admin_login(payload: LoginRequest):
    if not _configuration_is_valid():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Admin authentication is not configured. "
                "Set the STUFEED_ADMIN_EMAIL, STUFEED_ADMIN_PASSWORD, "
                "and STUFEED_SESSION_SECRET environment variables."
            ),
        )

    email = str(payload.email).strip().lower()

    email_matches = hmac.compare_digest(email, ADMIN_EMAIL)
    password_matches = hmac.compare_digest(
        payload.password,
        ADMIN_PASSWORD,
    )

    if not (email_matches and password_matches):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin email or password.",
        )

    return {
        "access_token": create_session_token(email),
        "token_type": "bearer",
        "expires_in": SESSION_DURATION_SECONDS,
        "email": ADMIN_EMAIL,
    }


@router.get("/me")
def check_admin_session():
    # The authentication middleware validates the bearer token first.
    return {"authenticated": True, "email": ADMIN_EMAIL}
