"""Admin smoke tests for the scheme models.

Proves, through the real admin views: every changelist renders (200), a
Scheme can be created and saved through the admin form, an invalid ``rules``
edit is rejected by ``Scheme.clean()``, and a saved scheme change invalidates
the memoized bundle (the next ``build(force=False)`` sees the DB change).
"""

import pytest
from django.test import Client

from apps.schemes import bundle
from apps.schemes.models import Scheme

pytestmark = pytest.mark.django_db

ADMIN_SCHEME_ID = "admin-test-scheme"

# Fields the admin Scheme form requires (no blank/default on the model).
_ADD_FIELDS = {
    "id": ADMIN_SCHEME_ID,
    "code": "ADM",
    "order": "990001",
    "benefit_type": "cash_transfer",
    "jurisdiction": "karnataka",
    "name": '{"en": "Admin test scheme"}',
    "summ": '{"en": "Summary"}',
    "department": '{"en": "Department"}',
    "benefit": '{"en": "Benefit"}',
    "amount": '{"en": "1,000"}',
    "deadline": '{"en": "March 31"}',
    "eligibility_criteria": "[]",
    "application_steps": "[]",
    "channels": "[]",
    "docs": "[]",
    "rules": '{"eligibility": [], "exclusions": [], "fixes": []}',
    "confidence_note": "screening_only",
    "last_verified": "2026-09-09",
    "source_url": "",
}

_EMPTY_RULES = '{"eligibility": [], "exclusions": [], "fixes": []}'


@pytest.fixture
def admin_client(imported):
    """A logged-in superuser test client (mobile is the USERNAME_FIELD)."""
    from apps.accounts.models import User

    user = User.objects.create_superuser(
        mobile="9800000001", password="admin-smoke-password-1"
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(autouse=True)
def plain_static_storage(settings):
    # The admin templates {% static %}-load hashed assets; the manifest
    # storage has no manifest until collectstatic runs, so swap to a plain
    # storage just for these tests.
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


def _scheme_change_url(scheme_id: str) -> str:
    return f"/admin/schemes/scheme/{scheme_id}/change/"


def test_all_changelists_render(admin_client):
    for url in (
        "/admin/schemes/scheme/",
        "/admin/schemes/question/",
        "/admin/schemes/reason/",
        "/admin/schemes/fix/",
        "/admin/schemes/incomebucket/",
    ):
        response = admin_client.get(url)
        assert response.status_code == 200, url


def _assert_saved(response) -> None:
    """A successful admin form submit redirects; on failure, show the errors."""
    assert response.status_code == 302, (
        response.context["adminform"].form.errors
        if response.context and "adminform" in response.context
        else None
    )


def test_admin_add_scheme(admin_client):
    response = admin_client.post("/admin/schemes/scheme/add/", _ADD_FIELDS)
    _assert_saved(response)

    scheme = Scheme.objects.get(id=ADMIN_SCHEME_ID)
    assert scheme.code == "ADM"
    assert scheme.name == {"en": "Admin test scheme"}
    assert scheme.rules == {"eligibility": [], "exclusions": [], "fixes": []}


def test_admin_change_view_makes_id_readonly(admin_client):
    scheme = Scheme.objects.create(
        id=ADMIN_SCHEME_ID,
        code="ADM",
        order=990001,
        name={"en": "Admin test scheme"},
        benefit_type="cash_transfer",
        jurisdiction="karnataka",
        last_verified="2026-09-09",
    )
    response = admin_client.get(_scheme_change_url(scheme.id))
    assert response.status_code == 200
    admin_form = response.context["adminform"]
    assert "id" in admin_form.readonly_fields


def test_admin_rejects_invalid_rules(admin_client):
    scheme = Scheme.objects.create(
        id=ADMIN_SCHEME_ID,
        code="ADM",
        order=990001,
        name={"en": "Admin test scheme"},
        benefit_type="cash_transfer",
        jurisdiction="karnataka",
        last_verified="2026-09-09",
    )

    bad_fields = dict(_ADD_FIELDS, rules='{"eligibility": [{"id": "e1", "check": {"op": "regex", "field": "bank", "value": "x"}, "on_fail": {"status": "not_eligible", "reason": {"code": "reason.infoMissing"}}}], "exclusions": [], "fixes": []}')
    response = admin_client.post(_scheme_change_url(scheme.id), bad_fields)
    # The form is redisplayed (not a redirect), carrying a rules error.
    assert response.status_code == 200
    form_errors = response.context["adminform"].form.errors
    assert "rules" in form_errors

    # The stored row is untouched.
    scheme.refresh_from_db()
    assert scheme.rules == {"eligibility": [], "exclusions": [], "fixes": [], "deep_check": []}


def test_admin_route_field_edit_and_empty_to_null(admin_client):
    scheme = Scheme.objects.create(
        id=ADMIN_SCHEME_ID,
        code="ADM",
        order=990001,
        name={"en": "Admin test scheme"},
        benefit_type="cash_transfer",
        jurisdiction="karnataka",
        last_verified="2026-09-09",
    )

    # The Routing section renders on the change form.
    response = admin_client.get(_scheme_change_url(scheme.id))
    assert response.status_code == 200
    assert "route" in response.context["adminform"].form.fields

    # A valid route value saves and persists.
    response = admin_client.post(
        _scheme_change_url(scheme.id),
        dict(_ADD_FIELDS, route='{"group": "vehicle", "value": "swavalambi-adcl"}'),
    )
    _assert_saved(response)
    scheme.refresh_from_db()
    assert scheme.route == {"group": "vehicle", "value": "swavalambi-adcl"}

    # An emptied box maps to null (the field's default), not an object.
    response = admin_client.post(_scheme_change_url(scheme.id), dict(_ADD_FIELDS, route=""))
    _assert_saved(response)
    scheme.refresh_from_db()
    assert scheme.route is None

    # An unknown route group is rejected by Scheme.clean() on submit.
    response = admin_client.post(
        _scheme_change_url(scheme.id),
        dict(_ADD_FIELDS, route='{"group": "bogus", "value": "x"}'),
    )
    assert response.status_code == 200
    form_errors = response.context["adminform"].form.errors
    assert "route" in form_errors
    scheme.refresh_from_db()
    assert scheme.route is None


def test_admin_save_invalidates_bundle_cache(admin_client):
    scheme = Scheme.objects.create(
        id=ADMIN_SCHEME_ID,
        code="ADM",
        order=990001,
        name={"en": "Old name"},
        benefit_type="cash_transfer",
        jurisdiction="karnataka",
        last_verified="2026-09-09",
    )

    # Warm the cache; it must contain the pre-edit name.
    bundle.reset_bundle()
    before = bundle.build(force=False)
    assert before.schemes_raw[0]["name"] == {"en": "Old name"} or any(
        raw["id"] == ADMIN_SCHEME_ID and raw["name"] == {"en": "Old name"}
        for raw in before.schemes_raw
    )

    # Save through the admin form (a real request, so the post_save signal
    # fires) with a changed name and a valid rules edit.
    new_fields = dict(
        _ADD_FIELDS,
        name='{"en": "New name"}',
        rules='{"eligibility": [{"id": "e1", "check": {"op": "equals", "field": "gender", "value": "f"}, "on_fail": {"status": "not_eligible", "reason": {"code": "reason.infoMissing"}}}], "exclusions": [], "fixes": []}',
    )
    response = admin_client.post(_scheme_change_url(scheme.id), new_fields)
    _assert_saved(response)

    # No force: the memoized bundle must have been dropped and rebuilt.
    after = bundle.build(force=False)
    raw = next(raw for raw in after.schemes_raw if raw["id"] == ADMIN_SCHEME_ID)
    assert raw["name"] == {"en": "New name"}
    assert raw["rules"]["eligibility"][0]["check"]["op"] == "equals"
