from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.schemes.models import Scheme


class Command(BaseCommand):
    help = "Import the seed JSON only when the database has no schemes yet."

    def add_arguments(self, parser):
        parser.add_argument("data_dir", nargs="?", default=None,
                            help="Data directory (default: DATA_DIR setting)")

    def handle(self, *args, **options):
        # Guard against a fresh volume where `migrate` has not run yet:
        # `Scheme.objects.exists()` would raise a confusing ProgrammingError.
        table = Scheme._meta.db_table
        if table not in connection.introspection.table_names():
            raise CommandError(
                f"Table '{table}' does not exist — run `manage.py migrate` first."
            )

        count = Scheme.objects.count()
        if count:
            self.stdout.write(
                f"Database already seeded ({count} schemes); skipping import. "
                "Run `manage.py import_json` to re-upsert the seed."
            )
            return

        data_dir = options["data_dir"] or str(settings.DATA_DIR)
        call_command("import_json", data_dir, stdout=self.stdout, stderr=self.stderr)
        self.stdout.write("Hydrated empty database from the seed data.")
