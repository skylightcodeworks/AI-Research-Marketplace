"""
Cookie-based auth for hardcoded super admin. No database needed (works on Vercel).
"""

from django.core.signing import Signer, BadSignature

# Hardcoded super admin
HARDCODED_ADMIN_EMAIL = "admin@skyapollo.com"
HARDCODED_ADMIN_PASSWORD = "skyapollo@admin123"

COOKIE_NAME = "skyapollo_admin"
# Value we store in the signed cookie (any fixed string)
COOKIE_PAYLOAD = "ok"


class HardcodedAdminUser:
    """Fake user object so middleware/views see an authenticated staff/superuser."""

    is_authenticated = True
    is_staff = True
    is_superuser = True
    pk = 0
    id = 0


def check_credentials(username: str, password: str) -> bool:
    email = (username or "").strip().lower()
    return email == HARDCODED_ADMIN_EMAIL and password == HARDCODED_ADMIN_PASSWORD


def make_signed_cookie_value() -> str:
    return Signer().sign(COOKIE_PAYLOAD)


def verify_signed_cookie(value: str) -> bool:
    if not value:
        return False
    try:
        Signer().unsign(value)
        return True
    except BadSignature:
        return False
