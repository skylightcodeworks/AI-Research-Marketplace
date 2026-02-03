"""
Middleware: require login for entire site. Only staff/superuser can access.
Unauthenticated or non-staff users are redirected to login page.
"""

from django.conf import settings
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from .cookie_auth import COOKIE_NAME, HardcodedAdminUser, verify_signed_cookie


class CookieAuthMiddleware(MiddlewareMixin):
    """
    If valid hardcoded-admin cookie is present, set request.user to a fake
    staff/superuser so the rest of the app sees the user as logged in (no DB).
    """

    def process_request(self, request):
        if not request.user.is_authenticated:
            raw = request.COOKIES.get(COOKIE_NAME)
            if raw and verify_signed_cookie(raw):
                request.user = HardcodedAdminUser()
        return None


class LoginRequiredMiddleware(MiddlewareMixin):
    """
    Redirect to login if user is not authenticated.
    Only staff/superuser can access the app (super admin only).
    """

    def process_request(self, request):
        path = request.path
        # Allow login, logout, and static files without auth
        if path == "/logout/":
            return None
        if path == "/login/":
            # Already logged-in staff/superuser → redirect to home
            if request.user.is_authenticated and (
                request.user.is_staff or request.user.is_superuser
            ):
                return redirect(settings.LOGIN_REDIRECT_URL)
            return None
        if path.startswith("/static/") or path == "/favicon.ico":
            return None
        # Require authenticated user
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        # Require staff or superuser (super admin only)
        if not (request.user.is_staff or request.user.is_superuser):
            return redirect(settings.LOGIN_URL)
        return None
