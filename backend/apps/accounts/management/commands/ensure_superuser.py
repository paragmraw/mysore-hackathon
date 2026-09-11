import os

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = (
        "Create the first superuser from DJANGO_SUPERUSER_MOBILE and "
        "DJANGO_SUPERUSER_PASSWORD, unless one already exists."
    )

    def handle(self, *args, **options):
        mobile = os.environ.get("DJANGO_SUPERUSER_MOBILE", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if not mobile or not password:
            return
        if User.objects.filter(is_superuser=True).exists():
            return
        try:
            User.objects.create_superuser(mobile=mobile, password=password)
        except (ValidationError, ValueError) as exc:
            raise CommandError(
                f"Invalid DJANGO_SUPERUSER_MOBILE/DJANGO_SUPERUSER_PASSWORD: {exc}"
            ) from exc
        self.stdout.write("Created superuser from DJANGO_SUPERUSER_MOBILE.")
