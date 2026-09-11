"""Read-endpoint tests: /health, /meta, /questions, /schemes (port of the
read-endpoint parts of api/tests/test_api.py, against the DB-imported data)."""

import pytest
from rest_framework.test import APIClient

from apps.schemes.bundle import get_bundle

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def client(imported):
    return APIClient()


@pytest.fixture(scope="module")
def bundle(imported, django_db_blocker):
    with django_db_blocker.unblock():
        return get_bundle()


# --------------------------------------------------------------------------
# /health, /meta
# --------------------------------------------------------------------------


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_counts(client, bundle):
    response = client.get("/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["schemes"] == len(bundle.schemes)
    assert body["schemes"] >= 2
    assert body["questions"] == len(bundle.questions)
    assert body["questions"] >= 22
    assert body["last_data_update"] == bundle.last_data_update


# --------------------------------------------------------------------------
# /questions
# --------------------------------------------------------------------------


def test_questions_ordered_and_localized(client):
    response = client.get("/questions", data={"locale": "en"})
    assert response.status_code == 200
    body = response.json()
    ids = [q["id"] for q in body]
    assert ids[0] == "age"
    assert ids[-1] == "pincode"
    assert ids.index("student") < ids.index("courseLevel")  # wizard order
    bank = next(q for q in body if q["id"] == "bank")
    assert bank["type"] == "single_select"
    assert [option["value"] for option in bank["options"]] == ["yes", "no"]
    for option in bank["options"]:
        assert option["label"]["en"]  # en always present
        assert option["label"]["kn"]  # kn present (translated or en fallback)
    assert bank["cols"] == 2
    disability = next(q for q in body if q["id"] == "disability")
    assert disability["optional"] is True
    farmer = next(q for q in body if q["id"] == "farmer")
    assert farmer["showIf"] == {"land": ["lt1acre", "1to5", "gt5"]}


def test_questions_kn_populated_with_fallback(client):
    # The kn pass may land before or after this test runs: every label must
    # carry a non-empty en and a non-empty kn (kn falls back to en when the
    # translation is missing).
    response = client.get("/questions", data={"locale": "kn"})
    assert response.status_code == 200
    body = response.json()
    for question in body:
        assert question["label"]["en"]
        assert question["label"]["kn"]


# --------------------------------------------------------------------------
# /questions stage/scheme_id filters
# --------------------------------------------------------------------------


def test_questions_stage_quick_returns_exactly_three(client):
    response = client.get("/questions", data={"stage": "quick"})
    assert response.status_code == 200
    ids = [q["id"] for q in response.json()]
    assert ids == ["age", "income", "employment"]


def test_questions_stage_full_excludes_deep(client):
    response = client.get("/questions", data={"stage": "full"})
    assert response.status_code == 200
    ids = [q["id"] for q in response.json()]
    assert "pincode" in ids
    assert not any(qid.startswith("dc_") for qid in ids)


def test_questions_stage_deep_returns_shared_core_only(client):
    response = client.get("/questions", data={"stage": "deep"})
    assert response.status_code == 200
    ids = [q["id"] for q in response.json()]
    assert "dc_aadhaar_name_match" in ids
    # Scheme extras are excluded without a scheme_id.
    assert "dc_ration_head" not in ids
    assert "dc_land_own_name" not in ids


def test_questions_stage_deep_with_scheme_id_adds_extras(client):
    response = client.get("/questions", data={"stage": "deep", "scheme_id": "gruha-lakshmi"})
    assert response.status_code == 200
    ids = [q["id"] for q in response.json()]
    assert "dc_aadhaar_name_match" in ids  # shared core
    assert "dc_ration_head" in ids  # gruha-lakshmi extra
    assert "dc_land_own_name" not in ids  # pm-kisan extra stays out


def test_questions_stage_deep_unknown_scheme_404(client):
    response = client.get("/questions", data={"stage": "deep", "scheme_id": "not-a-scheme"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown scheme: not-a-scheme"}


def test_questions_invalid_stage_422(client):
    response = client.get("/questions", data={"stage": "bogus"})
    assert response.status_code == 422
    assert response.json() == {"detail": "stage must be one of: quick, full, deep"}


# --------------------------------------------------------------------------
# /schemes
# --------------------------------------------------------------------------


def test_schemes_list_in_file_order(client, bundle):
    response = client.get("/schemes")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2
    assert body[0]["id"] == "gruha-lakshmi"  # file order preserved
    assert [s["id"] for s in body] == [s.id for s in bundle.schemes]
    record = next(s for s in body if s["id"] == "swavalambi-kmdc")
    # Phase 0 records use the category-value convention for route values.
    assert record["route"] == {"group": "vehicle", "value": "minority"}
    assert record["code"] == "KMV"
    assert record["rules"]["exclusions"], "rules included on list records"
    assert record["last_verified"]


def test_scheme_detail_and_404(client):
    response = client.get("/schemes/gruha-lakshmi")
    assert response.status_code == 200
    assert response.json()["code"] == "GLK"
    assert response.json()["name"]["en"] == "Gruha Lakshmi"

    response = client.get("/schemes/not-a-scheme")
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown scheme: not-a-scheme"}


# --------------------------------------------------------------------------
# 422 parity with the FastAPI validation the old endpoints relied on
# --------------------------------------------------------------------------


def test_read_endpoints_reject_bad_locale(client):
    for url, params in (
        ("/questions", {"locale": "fr"}),
        ("/schemes", {"locale": "fr"}),
        ("/schemes/gruha-lakshmi", {"locale": "fr"}),
    ):
        response = client.get(url, data=params)
        assert response.status_code == 422
