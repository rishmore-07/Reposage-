import base64

from cryptography.fernet import Fernet

from app.core.config import settings


def get_fernet_key(secret_key: str) -> bytes:
    """
    Derives a 32-byte url-safe base64-encoded key for Fernet
    from the application's SECRET_KEY.
    """
    # secret_key might be hex or random string, we need exactly 32 bytes.
    # We take the first 32 bytes of the utf-8 encoded string, pad if necessary.
    key_bytes = secret_key.encode("utf-8")
    if len(key_bytes) < 32:
        key_bytes = key_bytes.ljust(32, b"0")
    else:
        key_bytes = key_bytes[:32]
    return base64.urlsafe_b64encode(key_bytes)


def encrypt_string(data: str) -> str:
    """Encrypts a string using Fernet and the app's secret key."""
    if not data:
        return data
    f = Fernet(get_fernet_key(settings.secret_key))
    return f.encrypt(data.encode("utf-8")).decode("utf-8")


def decrypt_string(encrypted_data: str) -> str:
    """Decrypts a string using Fernet and the app's secret key."""
    if not encrypted_data:
        return encrypted_data
    f = Fernet(get_fernet_key(settings.secret_key))
    return f.decrypt(encrypted_data.encode("utf-8")).decode("utf-8")
