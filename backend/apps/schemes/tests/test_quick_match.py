"""POST /quick-match tests: the pre-login teaser from the three quick fields."""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

QUICK_ANSWERS = {"age": 30, "income": "2.5l-6l", "employment": "employed"}


@pytest.fixture(scope="module")
def client(imported):
    return APIClient()


def test_quick_match_happy_path(client):
    response = client.post(
        "/quick-match", {"locale": "en", "answers": QUICK_ANSWERS}, format="json"
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"results", "benefit_total", "hidden_route_groups"}
    assert set(body["benefit_total"]) == {"month", "one-time", "year"}

    by_id = {r["scheme_id"]: r for r in body["results"]}
    glk = by_id["gruha-lakshmi"]
    assert glk["status"] == "likely"
    assert glk["confidence"] == "likely"
    assert glk["amount_inr"] == 2000
    assert glk["amount_period"] == "month"
    assert glk["amount"]["en"]
    # Teaser rows carry no reasons/fixes/docs.
    assert set(glk) == {
        "scheme_id", "code", "name", "summ", "status", "confidence",
        "amount_inr", "amount_period", "amount",
    }
    # pm-kisan is a yearly cash transfer -> summed into the year bucket.
    assert body["benefit_total"]["year"] == 6000
    assert body["benefit_total"]["month"] >= 2000


def test_quick_match_benefit_total_skips_none_amounts(client):
    response = client.post(
        "/quick-match", {"answers": QUICK_ANSWERS}, format="json"
    )
    assert response.status_code == 200
    body = response.json()
    # In-kind schemes (amount_inr None) contribute nothing to any bucket.
    for result in body["results"]:
        if result["amount_inr"] is None:
            continue
        period = result["amount_period"]
        assert body["benefit_total"][period] >= result["amount_inr"]


def test_quick_match_missing_quick_field_422(client):
    for answers in (
        {"age": 30, "income": "2.5l-6l"},
        {"age": 30, "employment": "employed"},
        {"income": "2.5l-6l", "employment": "employed"},
        {},
    ):
        response = client.post("/quick-match", {"answers": answers}, format="json")
        assert response.status_code == 422, answers
        assert response.json() == {
            "detail": "answers must include age, income and employment"
        }


def test_quick_match_invalid_value_422(client):
    response = client.post(
        "/quick-match",
        {"answers": {**QUICK_ANSWERS, "employment": "astronaut"}},
        format="json",
    )
    assert response.status_code == 422
    assert "employment" in response.json()["detail"]


def test_quick_match_answers_must_be_object(client):
    response = client.post("/quick-match", {"answers": "x"}, format="json")
    assert response.status_code == 422
    assert response.json() == {"detail": "answers must be an object"}


def test_quick_match_bad_locale_422(client):
    response = client.post(
        "/quick-match", {"locale": "fr", "answers": QUICK_ANSWERS}, format="json"
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "locale must be one of: en, kn"}


def test_quick_match_route_gated_schemes_hidden(client):
    # No `category` answer -> every route-gated scheme stays hidden and its
    # group is reported.
    response = client.post(
        "/quick-match", {"answers": QUICK_ANSWERS}, format="json"
    )
    assert response.status_code == 200
    body = response.json()
    assert "postmatric" in body["hidden_route_groups"]
    assert "vehicle" in body["hidden_route_groups"]
    ids = {r["scheme_id"] for r in body["results"]}
    assert not any(sid.startswith("postmatric-") for sid in ids)
    assert "swavalambi-kmdc" not in ids
