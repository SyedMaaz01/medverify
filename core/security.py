import base64
import hashlib
import hmac
import uuid
from datetime import date
from typing import Optional

from .config import SECRET_KEY

SIGNING_KEY_VERSION = "v1"


def sign_batch_code(
    batch_id: uuid.UUID,
    batch_number: str,
    drug_name: str,
    expiry_date: date,
) -> str:
    """Generate versioned HMAC-SHA256 signed code for a batch."""
    message = (
        f"{SIGNING_KEY_VERSION}|{batch_id}|{batch_number}|{drug_name}|{expiry_date.isoformat()}"
    )
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{SIGNING_KEY_VERSION}.{b64}"


def verify_signature(
    signed_code: str,
    batch_id: uuid.UUID,
    batch_number: str,
    drug_name: str,
    expiry_date: date,
) -> bool:
    """Re-compute HMAC from DB record and compare (constant-time)."""
    expected = sign_batch_code(batch_id, batch_number, drug_name, expiry_date)
    return hmac.compare_digest(expected, signed_code)


def parse_signed_code(signed_code: str) -> Optional[str]:
    """Extract version from signed code, return version or None if malformed."""
    try:
        version, _ = signed_code.split(".", 1)
        return version
    except Exception:
        return None
