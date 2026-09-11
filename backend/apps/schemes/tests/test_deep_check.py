"""POST /deep-check tests: per-scheme document-verification refinement.

Requires a logged-in user whose profile already holds full-questionnaire
answers (the 400 gate). Deep answers are merged into the profile so they are
reused across schemes.
"""

import pytest

from apps.accounts.models import Profile, User
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

MOBILE = "9876543210"
PASSWORD = "s3cure-passphrase"
LOGIN = "/auth/login"
DEEP_CHECK = "/deep-check"

# Gruha Lakshmi qualifying answers (same fixture as test_match.py).
GL_ANSWERS = {
    "age": 34,
    "gender": "woman",
    "marital": "married",
    "student": "no",
    "education": "graduate",
    "category": "general",
    "ration": "bpl",
    "income": "6l-8l",
    "tax": "no",
    "land": "none",
    "womanhead": "yes",
    "electricity": "yes-own-name",
    "disability": "no",
    "bank": "yes",
    "aadhaar": "yes",
    "pincode": "570017",
}

DEEP_ALL_YES = {
    "dc_aadhaar_name_match": "yes",
    "dc_aadhaar_mobile_linked": "yes",
    "dc_aadhaar_bank_linked": "yes",
    "dc_bank_active": "yes",
    "dc_docs_ready": "yes",
    "dc_ration_head": "yes",
}


def make_client() -> APIClient:
    return APIClient()


def post_json(client, path, data):
    return client.post(path, data, format="json")


def logged_in_client_with_profile() -> APIClient:
    """A session-authenticated client whose user has full answers on file."""
    user = User.objects.create_user(MOBILE, PASSWORD)
    Profile.objects.create(user=user, answers=dict(GL_ANSWERS))
    client = make_client()
    post_json(client, LOGIN, {"mobile": MOBILE, "password": PASSWORD})
    return client


def test_deep_check_anonymous_401():
    response = make_client().post(
        DEEP_CHECK, {"scheme_id": "gruha-lakshmi", "answers": DEEP_ALL_YES}, format="json"
    )
    assert response.status_code == 401


def test_deep_check_without_profile_answers_400():
    User.objects.create_user(MOBILE, PASSWORD)
    client = make_client()
    post_json(client, LOGIN, {"mobile": MOBILE, "password": PASSWORD})

    response = client.post(
        DEEP_CHECK, {"scheme_id": "gruha-lakshmi", "answers": DEEP_ALL_YES}, format="json"
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Complete the questionnaire before a deep check."}


def test_deep_check_unknown_scheme_404():
    client = logged_in_client_with_profile()
    response = client.post(
        DEEP_CHECK, {"scheme_id": "not-a-scheme", "answers": DEEP_ALL_YES}, format="json"
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown scheme: not-a-scheme"}


def test_deep_check_rule_fires_blocked_with_fix():
    client = logged_in_client_with_profile()
    answers = {**DEEP_ALL_YES, "dc_aadhaar_name_match": "no"}
    response = client.post(
        DEEP_CHECK, {"scheme_id": "gruha-lakshmi", "answers": answers}, format="json"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scheme_id"] == "gruha-lakshmi"
    assert body["status"] == "blocked"
    assert body["reasons"][-1]["code"] == "reason.dcAadhaarNameMismatch"
    assert body["fixes"][-1]["fix_id"] == "aadhaar-name-bank-mismatch"
    assert body["fixes"][-1]["steps"], "fix playbook steps must be present"


def test_deep_check_all_pass_eligible():
    client = logged_in_client_with_profile()
    response = client.post(
        DEEP_CHECK, {"scheme_id": "gruha-lakshmi", "answers": DEEP_ALL_YES}, format="json"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "eligible"
    assert body["reasons"] == []
    assert body["fixes"] == []


def test_deep_check_persists_answers_to_profile():
    client = logged_in_client_with_profile()
    answers = {**DEEP_ALL_YES, "dc_bank_active": "no"}
    response = client.post(
        DEEP_CHECK, {"scheme_id": "gruha-lakshmi", "answers": answers}, format="json"
    )
    assert response.status_code == 200
    profile = User.objects.get(mobile=MOBILE).profile
    assert profile.deep_check_answers["dc_bank_active"] == "no"
    assert profile.deep_check_answers["dc_aadhaar_name_match"] == "yes"


def test_deep_check_merges_across_schemes():
    client = logged_in_client_with_profile()
    # First deep check on gruha-lakshmi stores the shared-core answers.
    client.post(
        DEEP_CHECK, {"scheme_id": "gruha-lakshmi", "answers": DEEP_ALL_YES}, format="json"
    )
    # A second scheme's deep check reuses them and adds its own extra.
    response = client.post(
        DEEP_CHECK,
        {"scheme_id": "pm-kisan", "answers": {"dc_land_own_name": "yes"}},
        format="json",
    )
    assert response.status_code == 200
    profile = User.objects.get(mobile=MOBILE).profile
    assert profile.deep_check_answers["dc_aadhaar_name_match"] == "yes"
    assert profile.deep_check_answers["dc_land_own_name"] == "yes"


def test_deep_check_bad_locale_422():
    client = logged_in_client_with_profile()
    response = client.post(
        DEEP_CHECK,
        {"locale": "fr", "scheme_id": "gruha-lakshmi", "answers": DEEP_ALL_YES},
        format="json",
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "locale must be one of: en, kn"}


def test_deep_check_answers_must_be_object():
    client = logged_in_client_with_profile()
    response = client.post(
        DEEP_CHECK, {"scheme_id": "gruha-lakshmi", "answers": "x"}, format="json"
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "answers must be an object"}
