"""Model-level tests for Scheme.clean() contract validation."""

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.schemes.models import Scheme


def make_scheme(**overrides) -> Scheme:
    fields = {
        "id": "test-scheme",
        "code": "TS",
        "order": 0,
        "name": {"en": "Test scheme"},
        "benefit_type": "cash_transfer",
        "jurisdiction": "karnataka",
        "rules": {"eligibility": [], "exclusions": [], "fixes": []},
        "last_verified": "2026-09-09",
    }
    fields.update(overrides)
    return Scheme(**fields)


def test_clean_passes_for_valid_scheme():
    make_scheme().clean()  # no raise


def test_clean_rejects_bad_route_group():
    scheme = make_scheme(route={"group": "unknown-group", "value": "x"})
    with pytest.raises(DjangoValidationError) as exc:
        scheme.clean()
    assert "route" in exc.value.message_dict


def test_clean_rejects_unknown_route_value():
    scheme = make_scheme(route={"group": "postmatric", "value": "bogus-value"})
    with pytest.raises(DjangoValidationError) as exc:
        scheme.clean()
    assert "route" in exc.value.message_dict
    assert "bogus-value" in str(exc.value)


def test_clean_rejects_unknown_check_op():
    scheme = make_scheme(
        rules={
            "eligibility": [
                {
                    "id": "e1",
                    "check": {"op": "regex", "field": "bank", "value": "x"},
                    "on_fail": {"status": "not_eligible", "reason": {"code": "reason.infoMissing"}},
                }
            ],
            "exclusions": [],
            "fixes": [],
        },
    )
    with pytest.raises(DjangoValidationError) as exc:
        scheme.clean()
    assert "rules" in exc.value.message_dict


def test_clean_wraps_pydantic_rule_errors():
    # Structurally invalid rule (missing on_fail): the raw pydantic error must
    # surface as a Django ValidationError on the 'rules' field.
    scheme = make_scheme(
        rules={
            "eligibility": [{"id": "e1", "check": {"op": "equals", "field": "bank", "value": "x"}}],
            "exclusions": [],
            "fixes": [],
        },
    )
    with pytest.raises(DjangoValidationError) as exc:
        scheme.clean()
    assert "rules" in exc.value.message_dict


def test_clean_rejects_bad_choice_values():
    with pytest.raises(DjangoValidationError) as exc:
        make_scheme(benefit_type="lottery").clean()
    assert "benefit_type" in exc.value.message_dict
    with pytest.raises(DjangoValidationError) as exc:
        make_scheme(jurisdiction="mars").clean()
    assert "jurisdiction" in exc.value.message_dict


def test_ordering_is_by_order():
    assert Scheme._meta.ordering == ["order"]
