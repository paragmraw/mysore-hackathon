"""hydrate tests: the seed-if-empty wrapper around ``import_json``."""

from datetime import date
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

from apps.csc.models import CscCenter, PincodeCentroid
from apps.schemes.models import Fix, IncomeBucket, Question, Reason, Scheme
from apps.schemes.tests.test_import_json import (
    EXPECTED_COUNTS,
    REPO_DATA,
    assert_counts,
    run_import,
)


def run_hydrate(data_dir: Path = REPO_DATA):
    out, err = StringIO(), StringIO()
    call_command("hydrate", str(data_dir), stdout=out, stderr=err)
    return out, err


def clear_seed_tables():
    """Delete every seed row so the next hydrate sees an empty database.

    The session-scoped ``imported`` fixture (backend/conftest.py) may have
    filled the test DB before this module runs, and hydrate only acts on an
    empty one.
    """
    Scheme.objects.all().delete()
    Question.objects.all().delete()
    Reason.objects.all().delete()
    Fix.objects.all().delete()
    IncomeBucket.objects.all().delete()
    CscCenter.objects.all().delete()
    PincodeCentroid.objects.all().delete()


@pytest.mark.django_db
def test_hydrates_empty_database_with_expected_counts():
    clear_seed_tables()
    out, _err = run_hydrate()
    assert_counts()
    assert "Hydrated empty database" in out.getvalue()
    # The import output is forwarded verbatim.
    assert "schemes: 19" in out.getvalue()


@pytest.mark.django_db
def test_noop_on_seeded_database_and_preserves_admin_edits():
    clear_seed_tables()
    run_import()
    assert_counts()

    # An admin edits one scheme and adds one that is absent from the seed.
    scheme = Scheme.objects.get(id="gruha-lakshmi")
    edited = dict(scheme.name)
    edited["en"] = "Admin edited title"
    scheme.name = edited
    scheme.save()
    Scheme.objects.create(
        id="admin-added", code="admin-added", order=9999, name={"en": "Admin added"},
        last_verified=date(2025, 1, 1),
    )

    out, _err = run_hydrate()
    assert Scheme.objects.filter(id="admin-added").exists()
    assert Scheme.objects.get(id="gruha-lakshmi").name == edited
    assert Scheme.objects.count() == EXPECTED_COUNTS["schemes"] + 1
    assert "already seeded" in out.getvalue()
    assert "Hydrated empty database" not in out.getvalue()


@pytest.mark.django_db
def test_fails_when_data_dir_missing(tmp_path):
    clear_seed_tables()
    with pytest.raises(CommandError):
        run_hydrate(tmp_path / "no-such-dir")


@pytest.mark.django_db
def test_fails_when_tables_missing():
    clear_seed_tables()
    # DDL is transactional in SQLite, so dropping the table here is undone
    # by pytest-django's rollback at the end of the test.
    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE {Scheme._meta.db_table}")
    with pytest.raises(CommandError) as exc:
        run_hydrate()
    assert Scheme._meta.db_table in str(exc.value)
    assert "migrate" in str(exc.value)
