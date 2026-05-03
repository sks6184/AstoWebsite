from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.utils.text import slugify


class AutoUsernameSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if not user.username:
            user.username = self._unique_username(data, user.email)
        return user

    def _unique_username(self, data, email):
        User = get_user_model()
        base = (
            data.get("username")
            or data.get("name")
            or data.get("email")
            or email
            or "user"
        )
        base = slugify(str(base).split("@")[0]).replace("-", "_") or "user"
        username = base[:140]
        counter = 1

        while User.objects.filter(username=username).exists():
            suffix = f"_{counter}"
            username = f"{base[:150 - len(suffix)]}{suffix}"
            counter += 1

        return username
