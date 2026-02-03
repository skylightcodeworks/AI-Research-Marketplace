"""
Auth views: cookie-based login/logout for hardcoded admin (no DB required).
"""

from django.conf import settings
from django.shortcuts import redirect, render
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .cookie_auth import (
    COOKIE_NAME,
    check_credentials,
    make_signed_cookie_value,
    verify_signed_cookie,
)


@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """Login with hardcoded credentials; set signed cookie on success (no DB)."""
    if request.method == "GET":
        # Already "logged in" via cookie?
        if request.COOKIES.get(COOKIE_NAME) and verify_signed_cookie(
            request.COOKIES.get(COOKIE_NAME, "")
        ):
            return redirect(settings.LOGIN_REDIRECT_URL)
        return render(request, "registration/login.html", {"form": None})

    username = (request.POST.get("username") or "").strip()
    password = request.POST.get("password") or ""

    if not check_credentials(username, password):
        return render(
            request,
            "registration/login.html",
            {
                "form": None,
                "error": "Invalid email or password.",
                "username_value": username,
            },
        )

    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or settings.LOGIN_REDIRECT_URL
    )
    if next_url == "/login/":
        next_url = settings.LOGIN_REDIRECT_URL
    response = redirect(next_url)
    response.set_cookie(
        COOKIE_NAME,
        make_signed_cookie_value(),
        max_age=60 * 60 * 24 * 7,  # 7 days
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
    )
    return response


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Clear auth cookie and redirect to login."""
    response = redirect(settings.LOGOUT_REDIRECT_URL)
    response.delete_cookie(COOKIE_NAME)
    return response
