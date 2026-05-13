"""
Auth Security Utilities — Password hashing and verification
"""

import hashlib
import hmac
import secrets


def hash_password(plain: str) -> str:
    """SHA-256 PBKDF2 z losową solą — bezpieczne bez bcrypt."""
    salt = secrets.token_hex(16)
    key  = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 260_000)
    return f"pbkdf2:sha256:260000:{salt}:{key.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    """Weryfikuje hasło względem przechowywanego hasha."""
    try:
        _, algo, iterations, salt, stored_hex = stored.split(":")
        key = hashlib.pbkdf2_hmac(algo, plain.encode(), salt.encode(), int(iterations))
        return hmac.compare_digest(key.hex(), stored_hex)
    except (ValueError, TypeError):
        return False
