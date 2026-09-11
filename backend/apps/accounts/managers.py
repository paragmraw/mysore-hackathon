from django.contrib.auth.base_user import BaseUserManager


class MobileUserManager(BaseUserManager):

    use_in_migrations = True

    def _create_user(self, mobile, password, **extra_fields):
        from apps.accounts.models import normalize_mobile

        if not mobile:
            raise ValueError("A mobile number must be provided")
        user = self.model(mobile=normalize_mobile(mobile), **extra_fields)
        user.set_password(password or "")
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_user(self, mobile, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(mobile, password, **extra_fields)

    def create_superuser(self, mobile, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(mobile, password, **extra_fields)
