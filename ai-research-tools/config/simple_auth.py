from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


ADMIN_EMAIL = "admin@skyapollo.com"
ADMIN_PASSWORD = "skyapollo@admin123"


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip().lower()
        password = request.POST.get("password") or ""

        if username == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            request.session["super_admin"] = True
            return redirect(settings.LOGIN_REDIRECT_URL)

        return render(
            request,
            "registration/login.html",
            {
                "error": "Invalid credentials.",
                "username": request.POST.get("username", ""),
            },
            status=401,
        )

    return render(request, "registration/login.html")


@require_http_methods(["POST", "GET"])
def logout_view(request):
    # Clear signed-cookie session
    try:
        request.session.flush()
    except Exception:
        request.session.clear()
    return redirect(settings.LOGOUT_REDIRECT_URL)
