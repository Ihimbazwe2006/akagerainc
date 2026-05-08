import os
import secrets
import string
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

LICENSE_KEY_LENGTH = int(os.getenv("LICENSE_KEY_LENGTH", 10))


def generate_license_key(length: int = LICENSE_KEY_LENGTH) -> str:
    """
    Generate a secure random license key.
    Format: Uppercase letters and numbers only
    Example: A7K9Z3P2QX
    """
    characters = string.ascii_uppercase + string.digits
    license_key = ''.join(secrets.choice(characters) for _ in range(length))
    return license_key


def hash_password(password: str) -> str:
    """Hash a password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return hash_password(password) == hashed_password


def get_license_expiry_date(days: int = 365) -> datetime:
    """Get license expiry date (default 1 year from now)"""
    return datetime.utcnow() + timedelta(days=days)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount with currency"""
    if currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "RWF":
        return f"RWF {amount:,.0f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def get_request_ip(request) -> str:
    """Extract client IP from request"""
    if request.client:
        return request.client.host
    return "Unknown"
