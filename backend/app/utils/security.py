import hmac
import hashlib
from app.config import get_settings

def generate_session_signature(session_id: str, exp: str) -> str:
    """
    Generate an HMAC SHA256 signature for a session.
    """
    settings = get_settings()
    secret = settings.INTERVIEW_SESSION_SECRET.encode("utf-8")
    message = f"{session_id}:{exp}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()

def verify_session_signature(session_id: str, exp: str, sig: str) -> bool:
    """
    Verify the HMAC SHA256 signature for a session.
    """
    if not session_id or not exp or not sig:
        return False
    expected_sig = generate_session_signature(session_id, exp)
    return hmac.compare_digest(expected_sig, sig)

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
