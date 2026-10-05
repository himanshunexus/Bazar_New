from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the configured Django superuser if it does not already exist."

    def handle(self, *args, **options):
        username = self._env("DJANGO_SUPERUSER_USERNAME")
        email = self._env("DJANGO_SUPERUSER_EMAIL")
        password = self._env("DJANGO_SUPERUSER_PASSWORD")
        if not all((username, email, password)):
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            return
        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created superuser {username}."))

    @staticmethod
    def _env(name):
        import os

        return os.environ.get(name, "").strip()
