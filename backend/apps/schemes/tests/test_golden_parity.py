"""Golden parity: Django responses vs snapshots captured from the old FastAPI
service (``python -m uvicorn api.main:app --port 8000`` with the default
``data/``), stored under ``backend/tests/golden/``.

Bodies are compared as parsed JSON (key-order-insensitive deep equality).
The limit-bound snapshots assert status parity only — the old 422 detail is
FastAPI's pydantic validation list, which the hand-rolled Django 422
intentionally replaces with a plain ``detail`` string.
"""

import json
from pathlib import Path

import pytest
from rest_framework.test import APIClient

GOLDEN = Path(__file__).resolve().parents[3] / "tests" / "golden"

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def client(imported):
    return APIClient()


def _load_snapshot(name: str) -> tuple[int, object]:
    """``(status, parsed_body)`` from a golden snapshot file."""
    path = GOLDEN / name
    if path.suffix == ".json":
        return 200, json.loads(path.read_text(encoding="utf-8"))
    # .txt files carry "<body>\n<status>" (captured with curl -w).
    body, status = path.read_text(encoding="utf-8").rsplit("\n", 1)
    return int(status), json.loads(body)


def _assert_par(client, url: str, params: dict, snapshot: str, *, status_only: bool = False):
    response = client.get(url, data=params)
    golden_status, golden_body = _load_snapshot(snapshot)
    assert response.status_code == golden_status
    if status_only:
        return
    assert response.json() == golden_body


def test_golden_meta(client):
    _assert_par(client, "/meta", {}, "meta.json")


def test_golden_questions_en(client):
    _assert_par(client, "/questions", {"locale": "en"}, "questions-en.json")


def test_golden_questions_kn(client):
    _assert_par(client, "/questions", {"locale": "kn"}, "questions-kn.json")


def test_golden_schemes_kn(client):
    _assert_par(client, "/schemes", {"locale": "kn"}, "schemes-kn.json")


def test_golden_scheme_detail_kn(client):
    _assert_par(
        client, "/schemes/gruha-lakshmi", {"locale": "kn"}, "scheme-gruha-lakshmi-kn.json"
    )


def test_golden_csc_exact_pincode(client):
    _assert_par(client, "/csc", {"pincode": "570001"}, "csc-570001.json")


def test_golden_csc_nearby_pincode(client):
    # 571603 has a centroid but no exact-centre pincode -> "nearby".
    _assert_par(client, "/csc", {"pincode": "571603"}, "csc-571603-nearby.json")


def test_golden_csc_district_fallback(client):
    # 560001 is valid Karnataka but outside the centroid map -> fallback.
    _assert_par(client, "/csc", {"pincode": "560001"}, "csc-560001-fallback.json")


def test_golden_csc_not_karnataka(client):
    _assert_par(client, "/csc", {"pincode": "110001"}, "csc-110001-notkarnataka.txt")


def test_golden_csc_limit_bounds_422(client):
    _assert_par(
        client, "/csc", {"pincode": "570001", "limit": 0}, "csc-570001-limit0.txt",
        status_only=True,
    )
    _assert_par(
        client, "/csc", {"pincode": "570001", "limit": 26}, "csc-570001-limit26.txt",
        status_only=True,
    )


def test_golden_scheme_404(client):
    response = client.get("/schemes/not-a-scheme")
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown scheme: not-a-scheme"}


# --------------------------------------------------------------------------
# POST /match — captured from the old service with the fixture answers and
# synthetic permutations (all-null, a partial minority-routed subset).
# --------------------------------------------------------------------------


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


def _assert_match_par(client, payload: dict, snapshot: str):
    response = client.post("/match", payload, format="json")
    golden_status, golden_body = _load_snapshot(snapshot)
    assert response.status_code == golden_status
    assert response.json() == golden_body


def test_golden_match_fixture_en(client):
    _assert_match_par(
        client, {"locale": "en", "answers": GL_ANSWERS}, "match-fixture-gruha-lakshmi-en.json"
    )


def test_golden_match_fixture_kn(client):
    _assert_match_par(
        client, {"locale": "kn", "answers": GL_ANSWERS}, "match-fixture-gruha-lakshmi-kn.json"
    )


def test_golden_match_all_null(client):
    answers = {q: None for q in [
        "age", "gender", "marital", "student", "courseLevel", "education",
        "category", "ration", "income", "tax", "land", "farmer", "womanhead",
        "electricity", "otherpension", "disability", "disabilitypct",
        "drivinglicence", "unemployed", "bank", "aadhaar", "pincode",
    ]}
    _assert_match_par(client, {"locale": "en", "answers": answers}, "match-all-null.json")


def test_golden_match_partial_minority(client):
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
    _assert_match_par(client, {"locale": "en", "answers": answers}, "match-partial-minority.json")


def test_golden_match_unknown_key_422(client):
    response = client.post("/match", {"answers": {"not_a_question": "x"}}, format="json")
    golden_status, golden_body = _load_snapshot("match-unknown-key-422.txt")
    assert response.status_code == golden_status
    assert response.json() == golden_body
