from django.contrib import admin
from django.urls import path, include
from apps.accounts import views as accounts_views  # import your dashboard view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", accounts_views.dashboard, name="home"),  # or redirect, your choice
    path(
        "dashboard/", accounts_views.dashboard, name="dashboard"
    ),  # <-- direct mapping
    path(
        "resume/",
        include(
            ("apps.resume_analysis.urls", "resume_analysis"),
            namespace="resume_analysis",
        ),
    ),
    path("accounts/", include("apps.accounts.urls")),
]
