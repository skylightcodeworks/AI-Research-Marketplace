"""
Middleware: require login for entire site. Only staff/superuser can access.
Unauthenticated or non-staff users are redirected to login page.
"""

from django.conf import settings
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin


class LoginRequiredMiddleware(MiddlewareMixin):
    """
    DB-free auth gate for serverless deploys (Vercel).
    Uses signed-cookie session flag `super_admin=True`.
    """

    def process_request(self, request):
        path = request.path
        # Allow login, logout, and static files without auth
        if path == "/logout/":
            return None
        if path == "/login/":
            # Already logged-in → redirect to home
            if request.session.get("super_admin") is True:
                return redirect(settings.LOGIN_REDIRECT_URL)
            return None
        if path.startswith("/static/") or path == "/favicon.ico":
            return None

        # Require super admin session
        if request.session.get("super_admin") is not True:
            return redirect(settings.LOGIN_URL)
        return None
