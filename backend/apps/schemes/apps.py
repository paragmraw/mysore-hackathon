from django.apps import AppConfig


class SchemesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.schemes"

    def ready(self) -> None:
        from apps.schemes import bundle

        bundle.connect_signals()
