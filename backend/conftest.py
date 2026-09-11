"""Shared pytest fixtures for the backend test suite.

The endpoint/engine tests need the contract data imported into the (empty)
test database exactly once per session; ``import_json`` is idempotent, so a
re-run is harmless.
"""

import pytest
from django.conf import settings
from django.core.management import call_command


@pytest.fixture(scope="session")
def imported(django_db_setup, django_db_blocker):
    """Import the repo's real ``data/`` into the test DB (session-scoped)."""
    with django_db_blocker.unblock():
        call_command("import_json", str(settings.DATA_DIR))
    return True
