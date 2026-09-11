"""Contract validation tests, ported from ``api/tests/test_loader.py``.

Same cases as the loader suite, but over in-memory dicts — the backend's
``contract.py`` module does no file I/O (the import command reads files).
"""

import copy

import pytest
from pydantic import ValidationError

from apps.schemes.engine.contract import (
    DataBundle,
    Localized,
    Question,
    ReasonDef,
    FixDef,
    SchemeRecord,
    loc,
    loc_out,
    validate_bundle,
)


# --------------------------------------------------------------------------
# Fixtures: synthetic dataset (mirrors the loader test's base_dataset)
# --------------------------------------------------------------------------


def base_dataset() -> dict:
    return {
        "questions.json": [
            {"id": "age", "type": "number", "label": {"en": "Age?", "kn": "Age?"}},
            {
                "id": "bank",
                "type": "single_select",
                "label": {"en": "Bank?", "kn": "Bank?"},
                "options": [
                    {"value": "yes", "label": {"en": "Yes", "kn": "Yes"}},
                    {"value": "no", "label": {"en": "No", "kn": "No"}},
                ],
            },
            {
                "id": "income",
                "type": "single_select",
                "label": {"en": "Income?", "kn": "Income?"},
                "options": [{"value": "lt-32k", "label": {"en": "Below 32k", "kn": "Below 32k"}}],
            },
        ],
        "schemes.json": {
            "schemes": [
                {
                    "id": "s1",
                    "code": "S1",
                    "name": {"en": "Scheme 1", "kn": "Scheme 1"},
                    "last_verified": "2026-09-09",
                    "rules": {"eligibility": [], "exclusions": [], "fixes": []},
                }
            ]
        },
        "reasons.json": {"reason.infoMissing": {"message": {"en": "Missing."}}},
        "fixes.json": {
            "bank-aadhaar-link": {"title": {"en": "Fix", "kn": "Fix"}, "steps": []}
        },
        "income-buckets.json": {"lt-32k": {"min": 0, "upper": 32000}},
    }


def parse(dataset: dict) -> DataBundle:
    """Build a contract DataBundle from an in-memory dataset (no files)."""
    schemes_raw = dataset["schemes.json"]
    if isinstance(schemes_raw, dict):
        schemes_raw = schemes_raw["schemes"]
    schemes = [SchemeRecord.model_validate(raw) for raw in schemes_raw]
    questions_raw = dataset["questions.json"]
    questions = [Question.model_validate(raw) for raw in questions_raw]
    reasons = {
        code: ReasonDef.model_validate(spec) for code, spec in dataset["reasons.json"].items()
    }
    fixes = {fix_id: FixDef.model_validate(spec) for fix_id, spec in dataset["fixes.json"].items()}
    return DataBundle(
        schemes=schemes,
        schemes_raw=schemes_raw,
        questions=questions,
        reasons=reasons,
        fixes=fixes,
        income_buckets=dataset["income-buckets.json"],
        csc_centers=[],
        csc_centroids={},
    )


def validate(dataset: dict) -> tuple[list[str], list[str]]:
    """Parse + validate a dataset, returning (errors, warnings)."""
    # Re-parse from the (possibly mutated) raw dicts on every call.
    bundle = parse(dataset)
    return validate_bundle(
        bundle,
        bundle.schemes_raw,
        [q.model_dump(by_alias=True) for q in bundle.questions],
    )


# --------------------------------------------------------------------------
# Positive + localization helpers
# --------------------------------------------------------------------------


def test_valid_dataset_has_no_errors():
    errors, _warnings = validate(base_dataset())
    assert errors == []


def test_show_if_parsed_from_camel_case():
    dataset = base_dataset()
    dataset["questions.json"][0]["showIf"] = {"field": "bank", "equals": "no"}
    questions = [Question.model_validate(raw) for raw in dataset["questions.json"]]
    assert questions[0].show_if == {"field": "bank", "equals": "no"}


def test_loc_falls_back_to_en_when_kn_missing():
    only_en = Localized(en="English only")
    assert loc(only_en, "kn") == "English only"
    assert loc_out(only_en, "kn") == {"en": "English only", "kn": "English only"}
    both = Localized(en="English", kn="ಕನ್ನಡ")
    assert loc(both, "kn") == "ಕನ್ನಡ"
    assert loc_out(both, "kn") == {"en": "English", "kn": "ಕನ್ನಡ"}
    assert loc_out(both, "en") == {"en": "English", "kn": "ಕನ್ನಡ"}


# --------------------------------------------------------------------------
# Contract violations
# --------------------------------------------------------------------------


def test_unknown_reason_code_fails():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["rules"] = {
        "eligibility": [
            {
                "id": "e1",
                "check": {"op": "equals", "field": "bank", "value": "no"},
                "on_fail": {"status": "not_eligible", "reason": {"code": "reason.bogus"}},
            }
        ],
        "exclusions": [],
        "fixes": [],
    }
    errors, _ = validate(dataset)
    assert any("reason.bogus" in error for error in errors)


def test_unknown_fix_id_fails():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["rules"] = {
        "eligibility": [],
        "exclusions": [],
        "fixes": [
            {
                "id": "f1",
                "check": {"op": "equals", "field": "bank", "value": "no"},
                "reason": {"code": "reason.infoMissing"},
                "fix_id": "no-such-fix",
            }
        ],
    }
    errors, _ = validate(dataset)
    assert any("no-such-fix" in error for error in errors)


def test_duplicate_scheme_ids_fail():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"].append(
        copy.deepcopy(dataset["schemes.json"]["schemes"][0])
    )
    errors, _ = validate(dataset)
    assert any("duplicate scheme id: s1" in error for error in errors)


def test_bad_route_group_fails_and_unknown_value_warns():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["route"] = {"group": "unknown-group", "value": "x"}
    errors, _ = validate(dataset)
    assert any("unknown-group" in error for error in errors)

    dataset["schemes.json"]["schemes"][0]["route"] = {
        "group": "postmatric", "value": "bogus-value"
    }
    errors, warnings = validate(dataset)
    assert errors == []  # unknown value is a warning, not an error
    assert any("bogus-value" in warning for warning in warnings)


def test_missing_last_verified_fails():
    dataset = base_dataset()
    del dataset["schemes.json"]["schemes"][0]["last_verified"]
    errors, _ = validate(dataset)
    assert any("last_verified" in error for error in errors)


def test_unknown_check_field_fails():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["rules"] = {
        "eligibility": [
            {
                "id": "e1",
                "check": {"op": "equals", "field": "not_a_question", "value": "x"},
                "on_fail": {"status": "not_eligible", "reason": {"code": "reason.infoMissing"}},
            }
        ],
        "exclusions": [],
        "fixes": [],
    }
    errors, _ = validate(dataset)
    assert any("not_a_question" in error for error in errors)


def test_unknown_op_fails():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["rules"] = {
        "eligibility": [
            {
                "id": "e1",
                "check": {"op": "regex", "field": "bank", "value": "x"},
                "on_fail": {"status": "not_eligible", "reason": {"code": "reason.infoMissing"}},
            }
        ],
        "exclusions": [],
        "fixes": [],
    }
    errors, _ = validate(dataset)
    assert any("unknown check op 'regex'" in error for error in errors)


def test_income_lte_with_field_fails():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["rules"] = {
        "eligibility": [
            {
                "id": "e1",
                "check": {"op": "income_lte", "field": "income", "value": 32000},
                "on_fail": {"status": "not_eligible", "reason": {"code": "reason.infoMissing"}},
            }
        ],
        "exclusions": [],
        "fixes": [],
    }
    errors, _ = validate(dataset)
    assert any("income_lte" in error for error in errors)


def test_missing_income_question_fails():
    dataset = base_dataset()
    dataset["questions.json"] = [q for q in dataset["questions.json"] if q["id"] != "income"]
    errors, _ = validate(dataset)
    assert any("requires the 'income' question" in error for error in errors)


def test_missing_english_fails():
    dataset = base_dataset()
    scheme = dataset["schemes.json"]["schemes"][0]
    scheme["summ"] = {"kn": "Kannada only"}
    # The localized-coverage check runs on raw dicts, so 'summ' is caught either
    # by pydantic (en required) or by validate_bundle — here at parse time.
    with pytest.raises(ValidationError) as exc:
        parse(dataset)
    assert "summ" in str(exc.value)


def test_kn_equal_to_en_warns_but_loads():
    dataset = base_dataset()  # kn == en everywhere
    errors, warnings = validate(dataset)
    assert errors == []
    assert any("Kannada copy pending" in warning for warning in warnings)


def test_missing_kn_warns_but_loads():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["summ"] = {"en": "No Kannada"}
    errors, warnings = validate(dataset)
    assert errors == []
    assert any("Kannada copy pending" in warning for warning in warnings)


# --------------------------------------------------------------------------
# Task 1 additions: amount fields, question stage/scheme_id, deep_check rules
# --------------------------------------------------------------------------


def test_amount_fields_parse():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["amount_inr"] = 2000
    dataset["schemes.json"]["schemes"][0]["amount_period"] = "month"
    schemes = [SchemeRecord.model_validate(raw) for raw in dataset["schemes.json"]["schemes"]]
    assert schemes[0].amount_inr == 2000
    assert schemes[0].amount_period == "month"
    # Defaults when absent.
    assert SchemeRecord.model_validate(dataset["schemes.json"]["schemes"][0]).amount_inr == 2000
    assert SchemeRecord.model_validate(dataset["schemes.json"]["schemes"][0]).amount_period == "month"


def test_stage_and_scheme_id_parse():
    dataset = base_dataset()
    dataset["questions.json"][0]["stage"] = ["quick", "full"]
    dataset["questions.json"][0]["scheme_id"] = "s1"
    questions = [Question.model_validate(raw) for raw in dataset["questions.json"]]
    assert questions[0].stage == ["quick", "full"]
    assert questions[0].scheme_id == "s1"
    # Defaults when absent.
    assert questions[1].stage == ["full"]
    assert questions[1].scheme_id is None


def test_invalid_stage_value_fails():
    dataset = base_dataset()
    dataset["questions.json"][0]["stage"] = ["bogus"]
    errors, _ = validate(dataset)
    assert any("question age: invalid stage 'bogus'" in error for error in errors)


def test_scheme_id_on_non_deep_question_fails():
    dataset = base_dataset()
    dataset["questions.json"][0]["stage"] = ["full"]
    dataset["questions.json"][0]["scheme_id"] = "s1"
    errors, _ = validate(dataset)
    assert any("question age: scheme_id set on a non-deep question" in error for error in errors)


def test_unknown_scheme_id_fails():
    dataset = base_dataset()
    dataset["questions.json"][0]["stage"] = ["deep"]
    dataset["questions.json"][0]["scheme_id"] = "no-such-scheme"
    errors, _ = validate(dataset)
    assert any("question age: unknown scheme_id 'no-such-scheme'" in error for error in errors)


def test_valid_deep_check_passes():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["rules"] = {
        "eligibility": [],
        "exclusions": [],
        "fixes": [],
        "deep_check": [
            {
                "id": "dc1",
                "check": {"op": "equals", "field": "bank", "value": "no"},
                "reason": {"code": "reason.infoMissing"},
                "fix_id": "bank-aadhaar-link",
            }
        ],
    }
    errors, _ = validate(dataset)
    assert errors == []


def test_deep_check_rule_unknown_field_fails():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["rules"] = {
        "eligibility": [],
        "exclusions": [],
        "fixes": [],
        "deep_check": [
            {
                "id": "dc1",
                "check": {"op": "equals", "field": "not_a_question", "value": "no"},
                "reason": {"code": "reason.infoMissing"},
                "fix_id": "bank-aadhaar-link",
            }
        ],
    }
    errors, _ = validate(dataset)
    assert any("check field 'not_a_question' is not a question id" in error for error in errors)


def test_deep_check_rule_unknown_fix_fails():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["rules"] = {
        "eligibility": [],
        "exclusions": [],
        "fixes": [],
        "deep_check": [
            {
                "id": "dc1",
                "check": {"op": "equals", "field": "bank", "value": "no"},
                "reason": {"code": "reason.infoMissing"},
                "fix_id": "no-such-fix",
            }
        ],
    }
    errors, _ = validate(dataset)
    assert any("unknown fix_id 'no-such-fix'" in error for error in errors)


def test_deep_check_rule_unknown_reason_fails():
    dataset = base_dataset()
    dataset["schemes.json"]["schemes"][0]["rules"] = {
        "eligibility": [],
        "exclusions": [],
        "fixes": [],
        "deep_check": [
            {
                "id": "dc1",
                "check": {"op": "equals", "field": "bank", "value": "no"},
                "reason": {"code": "reason.bogus"},
                "fix_id": "bank-aadhaar-link",
            }
        ],
    }
    errors, _ = validate(dataset)
    assert any("unknown reason code 'reason.bogus'" in error for error in errors)


def test_quick_stage_missing_questions_warns():
    dataset = base_dataset()
    # Only 'bank' is quick; age/income/employment are not.
    dataset["questions.json"][1]["stage"] = ["quick"]
    errors, warnings = validate(dataset)
    assert errors == []
    assert any("quick stage lacks the 'age' question" in warning for warning in warnings)
    assert any("quick stage lacks the 'income' question" in warning for warning in warnings)
    assert any("quick stage lacks the 'employment' question" in warning for warning in warnings)


def test_quick_stage_complete_no_warning():
    dataset = base_dataset()
    for q in dataset["questions.json"]:
        q["stage"] = ["quick", "full"]
    # Add the employment question the quick stage requires.
    dataset["questions.json"].append(
        {
            "id": "employment",
            "type": "single_select",
            "label": {"en": "Employment?", "kn": "Employment?"},
            "options": [{"value": "unemployed", "label": {"en": "Unemployed", "kn": "Unemployed"}}],
            "stage": ["quick", "full"],
        }
    )
    errors, warnings = validate(dataset)
    assert errors == []
    assert not any("quick stage lacks" in warning for warning in warnings)
