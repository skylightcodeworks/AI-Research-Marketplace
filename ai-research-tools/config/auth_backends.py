"""
Custom auth backends: hardcoded super admin + email/username login.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()

# Hardcoded super admin (single fixed login)
HARDCODED_ADMIN_EMAIL = "admin@skyapollo.com"
HARDCODED_ADMIN_PASSWORD = "skyapollo@admin123"


class HardcodedAdminBackend(ModelBackend):
    """
    Authenticate using hardcoded super admin credentials only.
    Creates the admin user in DB if it doesn't exist (for first login).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        email = (username or "").strip().lower()
        if email != HARDCODED_ADMIN_EMAIL or password != HARDCODED_ADMIN_PASSWORD:
            return None
        user, _ = User.objects.get_or_create(
            username=HARDCODED_ADMIN_EMAIL,
            defaults={
                "email": HARDCODED_ADMIN_EMAIL,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if not user.is_staff or not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["is_staff", "is_superuser"])
        return user if self.user_can_authenticate(user) else None


class EmailOrUsernameBackend(ModelBackend):
    """
    Authenticate using email or username (for any other users if added later).
    If the given value contains '@', treat it as email; otherwise as username.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        if "@" in username:
            try:
                user = User.objects.get(email__iexact=username)
            except User.DoesNotExist:
                return None
        else:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
