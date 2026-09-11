"""POST /match tests (port of the /match cases of api/tests/test_api.py,
plus validation-error and cache-invalidation coverage against the DB-backed
bundle)."""

import pytest
from rest_framework.test import APIClient

from apps.schemes.bundle import get_bundle, reset_bundle
from apps.schemes.models import Scheme
from apps.schemes.views import _normalize_answers

pytestmark = pytest.mark.django_db

# Copy of api/tests/fixtures/answers_gruha_lakshmi.json (kept self-contained:
# the old api/ tree may be deleted once the migration lands).
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


@pytest.fixture(scope="module")
def client(imported):
    return APIClient()


# --------------------------------------------------------------------------
# Ports of the old /match tests
# --------------------------------------------------------------------------


def test_match_gruha_lakshmi_eligible(client):
    response = client.post("/match", {"locale": "en", "answers": GL_ANSWERS}, format="json")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"results", "hidden_route_groups"}
    by_id = {r["scheme_id"]: r for r in body["results"]}
    glk = by_id["gruha-lakshmi"]
    assert glk["status"] == "eligible"
    assert glk["confidence"] == "likely"
    assert glk["reasons"] == []
    assert glk["fixes"] == []
    assert glk["docs"][0]["en"] == "Aadhaar card"
    # general category routes to nothing -> the vehicle-group record is hidden.
    assert "vehicle" in body["hidden_route_groups"]
    assert "swavalambi-kmdc" not in by_id


def test_match_result_shape_and_order(client):
    bundle = get_bundle()
    response = client.post("/match", {"answers": GL_ANSWERS}, format="json")
    body = response.json()
    for result in body["results"]:
        assert set(result) == {
            "scheme_id", "code", "name", "summ", "status", "confidence",
            "reasons", "fixes", "matched_facts", "docs",
        }
    # Result order = scheme order (route-hidden schemes omitted).
    scheme_ids = [s.id for s in bundle.schemes]
    positions = [scheme_ids.index(r["scheme_id"]) for r in body["results"]]
    assert positions == sorted(positions)
    # hidden groups sorted
    assert body["hidden_route_groups"] == sorted(body["hidden_route_groups"])


def test_match_blocked_via_bank_no(client):
    answers = {**GL_ANSWERS, "bank": "no"}
    response = client.post("/match", {"answers": answers}, format="json")
    assert response.status_code == 200
    glk = next(r for r in response.json()["results"] if r["scheme_id"] == "gruha-lakshmi")
    assert glk["status"] == "blocked"
    assert glk["fixes"][0]["fix_id"] == "bank-aadhaar-link"
    assert glk["fixes"][0]["title"]["en"] == "Link your Aadhaar to your bank account"


def test_match_exclusion_wins(client):
    answers = {**GL_ANSWERS, "tax": "yes", "aadhaar": "no"}
    response = client.post("/match", {"answers": answers}, format="json")
    glk = next(r for r in response.json()["results"] if r["scheme_id"] == "gruha-lakshmi")
    assert glk["status"] == "not_eligible"
    assert [r["code"] for r in glk["reasons"]] == ["reason.incomeTaxPayer"]


def test_match_missing_answers_fail_info_missing(client):
    response = client.post("/match", {"answers": {}}, format="json")
    assert response.status_code == 200
    glk = next(r for r in response.json()["results"] if r["scheme_id"] == "gruha-lakshmi")
    assert glk["status"] == "not_eligible"
    assert glk["reasons"][0]["code"] == "reason.infoMissing"


def test_match_locale_kn_messages_present(client):
    response = client.post(
        "/match", {"locale": "kn", "answers": {**GL_ANSWERS, "tax": "yes"}}, format="json"
    )
    assert response.status_code == 200
    glk = next(r for r in response.json()["results"] if r["scheme_id"] == "gruha-lakshmi")
    message = glk["reasons"][0]["message"]
    assert message["en"]
    assert message["kn"]  # kn falls back to en while translation is pending
    assert glk["name"]["kn"]


def test_match_minority_routes_to_kmdc(client):
    answers = {
        "age": 30,
        "gender": "man",
        "student": "no",
        "education": "diploma",
        "category": "minority",
        "ration": "bpl",
        "income": "2.5l-6l",
        "tax": "no",
        "land": "none",
        "electricity": "yes-own-name",
        "drivinglicence": "yes",
        "bank": "yes",
        "aadhaar": "yes",
    }
    response = client.post("/match", {"answers": answers}, format="json")
    assert response.status_code == 200
    body = response.json()
    by_id = {r["scheme_id"]: r for r in body["results"]}
    kmdc = by_id.get("swavalambi-kmdc")
    assert kmdc is not None, "minority category must route to swavalambi-kmdc"
    assert kmdc["status"] == "eligible"


def test_match_defaults_locale_and_answers(client):
    # Old MatchBody: locale Literal default "en", answers default {}.
    response = client.post("/match", format="json")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"results", "hidden_route_groups"}


# --------------------------------------------------------------------------
# Validation-error parity (422 detail strings from _normalize_answers)
# --------------------------------------------------------------------------


def test_match_rejects_unknown_key(client):
    response = client.post("/match", {"answers": {"not_a_question": "x"}}, format="json")
    assert response.status_code == 422
    assert response.json() == {
        "detail": "Unknown answer key 'not_a_question': not a question id."
    }


def test_match_rejects_unknown_value(client):
    response = client.post("/match", {"answers": {"bank": "maybe"}}, format="json")
    assert response.status_code == 422
    assert "bank" in response.json()["detail"]
    assert response.json() == {
        "detail": "Invalid value 'maybe' for question 'bank'."
    }


def test_match_rejects_non_numeric_age(client):
    response = client.post("/match", {"answers": {"age": "thirty"}}, format="json")
    assert response.status_code == 422
    assert response.json() == {"detail": "Answer for 'age' must be a number."}


def test_match_rejects_bool_for_number(client):
    response = client.post("/match", {"answers": {"age": True}}, format="json")
    assert response.status_code == 422
    assert response.json() == {"detail": "Answer for 'age' must be a number."}


def test_match_rejects_bad_pincode(client):
    for pin in ("5600", "560001a", "5600011", "abc", "56000 "):
        response = client.post("/match", {"answers": {"pincode": pin}}, format="json")
        assert response.status_code == 422, pin
        assert response.json() == {
            "detail": "Answer for 'pincode' must be a 6-digit pincode."
        }


def test_match_accepts_int_pincode_via_str_coercion(client):
    # Old behavior: str(value) then digit check, so int 560001 is valid.
    response = client.post("/match", {"answers": {"pincode": 560001}}, format="json")
    assert response.status_code == 200


def test_match_rejects_bad_locale(client):
    response = client.post("/match", {"locale": "fr", "answers": {}}, format="json")
    assert response.status_code == 422
    response = client.post("/match", {"locale": "", "answers": {}}, format="json")
    assert response.status_code == 422


def test_match_answers_must_be_object(client):
    # FastAPI: answers: dict[str, Any] -> pydantic 422 on a non-object.
    response = client.post("/match", {"answers": "x"}, format="json")
    assert response.status_code == 422


def test_match_null_answers_pass_through(client):
    response = client.post(
        "/match", {"answers": {"disability": None, "pincode": None}}, format="json"
    )
    assert response.status_code == 200
    glk = next(r for r in response.json()["results"] if r["scheme_id"] == "gruha-lakshmi")
    # Optional question + required question both unanswered -> infoMissing.
    assert glk["status"] == "not_eligible"
    assert glk["reasons"][0]["code"] == "reason.infoMissing"


# --------------------------------------------------------------------------
# Number coercion (unit-level, exercising _normalize_answers directly)
# --------------------------------------------------------------------------


def test_normalize_number_coercion():
    bundle = get_bundle()
    normalized = _normalize_answers({"age": "34"}, bundle)
    assert normalized == {"age": 34}
    assert isinstance(normalized["age"], int)
    normalized = _normalize_answers({"age": 34.0}, bundle)
    assert normalized == {"age": 34}
    assert isinstance(normalized["age"], int)
    # Non-integral floats stay floats.
    assert _normalize_answers({"age": 34.5}, bundle) == {"age": 34.5}
    assert _normalize_answers({"age": "34.5"}, bundle) == {"age": 34.5}


# --------------------------------------------------------------------------
# Cache invalidation: an edited Scheme row must be reflected by /match
# --------------------------------------------------------------------------


def test_match_cache_invalidation_reflects_scheme_edit(client):
    scheme = Scheme.objects.get(id="gruha-lakshmi")
    original_rules = scheme.rules
    try:
        # Gut the rules: with no eligibility/exclusions/fixes, empty answers
        # evaluate to eligible (was not_eligible via reason.infoMissing).
        scheme.rules = {"eligibility": [], "exclusions": [], "fixes": []}
        scheme.save()  # post_save signal drops the memoized bundle
        response = client.post("/match", {"answers": {}}, format="json")
        assert response.status_code == 200
        glk = next(
            r for r in response.json()["results"] if r["scheme_id"] == "gruha-lakshmi"
        )
        assert glk["status"] == "eligible", "bundle must reflect the edited DB row"
    finally:
        scheme.rules = original_rules
        scheme.save()
        reset_bundle()
