"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from config.simple_auth import login_view, logout_view
from apollo_ingest.views import (
    company_search_view,
    CompanySearchAPIView,
    TagsSearchAPIView,
    PeopleSearchAPIView,
    export_companies_view,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth: login required for entire site
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    # UI
    path("", company_search_view, name="company_search"),
    path("openai-thinking/", include("openai_thinking.urls")),
    # API Endpoints
    path(
        "api/companies/search/",
        CompanySearchAPIView.as_view(),
        name="api_company_search",
    ),
    path("api/tags/search/", TagsSearchAPIView.as_view(), name="api_tags_search"),
    path("api/people/search/", PeopleSearchAPIView.as_view(), name="api_people_search"),
    path("api/export/companies/", export_companies_view, name="api_export_companies"),
    # Swagger / OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
