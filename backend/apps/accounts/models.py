import re

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.accounts.managers import MobileUserManager

MOBILE_REGEX = r"^[6-9]\d{9}$"


def normalize_mobile(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


class User(AbstractBaseUser, PermissionsMixin):

    mobile = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        validators=[RegexValidator(MOBILE_REGEX, "Enter a valid 10-digit Indian mobile number.")],
    )
    name = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = MobileUserManager()

    USERNAME_FIELD = "mobile"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["mobile"]

    def __str__(self) -> str:
        return self.mobile

    def clean(self) -> None:
        self.mobile = normalize_mobile(self.mobile)
        if not re.fullmatch(MOBILE_REGEX, self.mobile):
            raise DjangoValidationError(
                {"mobile": "Enter a valid 10-digit Indian mobile number."}
            )
        super().clean()

    def save(self, *args, **kwargs):
        self.mobile = normalize_mobile(self.mobile)
        super().save(*args, **kwargs)


class Profile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    answers = models.JSONField(default=dict)
    deep_check_answers = models.JSONField(default=dict)

    def __str__(self) -> str:
        return f"Profile({self.user.mobile})"
