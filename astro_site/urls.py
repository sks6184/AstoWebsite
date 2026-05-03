from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from .views import home


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("auth/", include("allauth.urls")),
    path("accounts/", include("accounts.urls")),
    path("charts/", include("charts.urls")),
    path("chat/", include("chat.urls")),
    path("payments/", include("payments.urls")),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password-reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
