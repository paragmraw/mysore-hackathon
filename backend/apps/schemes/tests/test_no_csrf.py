"""CSRF is disabled project-wide; a logged-in session must be able to POST
without any CSRF token.

A real Django test client defaults to enforce_csrf_checks=False, which sets
_dont_enforce_csrf_checks and skips DRF's check — so regression testing this
requires enforce_csrf_checks=True (a true browser never sends the bypass flag).
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

MOBILE = "9876500000"
PASSWORD = "s3cure-passphrase"


def make_browser_like_client() -> APIClient:
    return APIClient(enforce_csrf_checks=True)


def test_logged_in_session_post_has_no_csrf_failure(imported):
    User.objects.create_user(MOBILE, PASSWORD)
    client = make_browser_like_client()
    assert client.post(
        "/auth/login", {"mobile": MOBILE, "password": PASSWORD}, format="json"
    ).status_code == 200
    assert "sessionid" in client.cookies

    match = client.post(
        "/match",
        {"locale": "en", "answers": {"age": 34, "gender": "woman", "category": "general"}},
        format="json",
    )
    assert match.status_code == 200, match.content

    quick = client.post(
        "/quick-match",
        {"locale": "en", "answers": {"age": 30, "income": "2.5l-6l", "employment": "employed"}},
        format="json",
    )
    assert quick.status_code == 200, quick.content
