"""import_json tests against the repo's real ``data/`` (and a broken fixture)."""

import json
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.csc.models import CscCenter, PincodeCentroid
from apps.schemes.models import Fix, IncomeBucket, Question, Reason, Scheme

REPO_ROOT = Path(__file__).resolve().parents[4]
REPO_DATA = REPO_ROOT / "data"

# The exact counts the contract data must produce.
EXPECTED_COUNTS = {
    "schemes": 19,
    "questions": 34,
    "reasons": 38,
    "fixes": 15,
    "income_buckets": 5,
    "csc_centers": 37,
    "pincode_centroids": 35,
}


def run_import(data_dir: Path = REPO_DATA, **kwargs):
    out, err = StringIO(), StringIO()
    call_command("import_json", str(data_dir), stdout=out, stderr=err, **kwargs)
    return out, err


def assert_counts():
    assert Scheme.objects.count() == EXPECTED_COUNTS["schemes"]
    assert Question.objects.count() == EXPECTED_COUNTS["questions"]
    assert Reason.objects.count() == EXPECTED_COUNTS["reasons"]
    assert Fix.objects.count() == EXPECTED_COUNTS["fixes"]
    assert IncomeBucket.objects.count() == EXPECTED_COUNTS["income_buckets"]
    assert CscCenter.objects.count() == EXPECTED_COUNTS["csc_centers"]
    assert PincodeCentroid.objects.count() == EXPECTED_COUNTS["pincode_centroids"]


@pytest.fixture(name="imported")
def imported_fixture(db):
    run_import()
    assert_counts()
    return True


# --------------------------------------------------------------------------
# Real repo data
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_real_data_imports_with_expected_counts():
    out, _err = run_import()
    assert_counts()
    assert "schemes: 19" in out.getvalue()
    assert "pincode_centroids: 35" in out.getvalue()


@pytest.mark.django_db
def test_order_follows_file_array_index(imported):
    with (REPO_DATA / "schemes.json").open(encoding="utf-8") as fh:
        file_ids = [s["id"] for s in json.load(fh)["schemes"]]
    db_ids = list(Scheme.objects.values_list("id", flat=True))
    assert db_ids == file_ids  # Meta.ordering = ["order"]

    with (REPO_DATA / "questions.json").open(encoding="utf-8") as fh:
        q_ids = [q["id"] for q in json.load(fh)]
    assert list(Question.objects.values_list("id", flat=True)) == q_ids
    assert Question.objects.get(id="age").order == 0
    assert Question.objects.get(id="pincode").order == 22

    with (REPO_DATA / "income-buckets.json").open(encoding="utf-8") as fh:
        bucket_ids = list(json.load(fh))
    assert list(IncomeBucket.objects.values_list("id", flat=True)) == bucket_ids


@pytest.mark.django_db
def test_spot_check_field_values(imported):
    scheme = Scheme.objects.get(id="gruha-lakshmi")
    assert scheme.code
    assert scheme.name["en"]
    assert scheme.last_verified is not None
    assert scheme.rules["eligibility"] or scheme.rules["exclusions"] or scheme.rules["fixes"]
    assert scheme.amount_inr == 2000
    assert scheme.amount_period == "month"
    assert scheme.rules["deep_check"]  # every scheme carries deep-check rules

    pm_kisan = Scheme.objects.get(id="pm-kisan")
    assert pm_kisan.amount_inr == 6000
    assert pm_kisan.amount_period == "year"

    yuva_nidhi = Scheme.objects.get(id="yuva-nidhi")
    assert any(r["id"] == "yn-e-emp" for r in yuva_nidhi.rules["eligibility"])

    q = Question.objects.get(id="pincode")
    assert q.type == "pincode"
    assert q.optional is True
    assert q.show_if is None
    assert q.stage == ["full"]
    assert q.scheme_id is None

    age = Question.objects.get(id="age")
    assert age.stage == ["quick", "full"]
    employment = Question.objects.get(id="employment")
    assert employment.stage == ["quick", "full"]
    dc_ration = Question.objects.get(id="dc_ration_head")
    assert dc_ration.stage == ["deep"]
    assert dc_ration.scheme_id == "gruha-lakshmi"

    # showIf from the JSON is stored under the snake_case show_if field.
    with (REPO_DATA / "questions.json").open(encoding="utf-8") as fh:
        with_show_if = next(q for q in json.load(fh) if "showIf" in q)
    assert Question.objects.get(id=with_show_if["id"]).show_if == with_show_if["showIf"]

    assert Reason.objects.get(code="reason.infoMissing").message["en"]
    fix = Fix.objects.get(id="bank-aadhaar-link")
    assert fix.title["en"]
    assert fix.steps

    bucket = IncomeBucket.objects.get(id="lt-32k")
    assert bucket.min == 0 and bucket.upper == 32000
    assert IncomeBucket.objects.get(id="gt-8l").upper is None  # open-ended

    center = CscCenter.objects.first()
    assert center.pincode.isdigit() and len(center.pincode) == 6
    assert -90 <= center.lat <= 90 and -180 <= center.lng <= 180


@pytest.mark.django_db
def test_import_is_idempotent():
    run_import()
    keyed = [(Scheme, "id"), (Question, "id"), (Reason, "code"), (Fix, "id"),
             (IncomeBucket, "id"), (CscCenter, "id"), (PincodeCentroid, "pincode")]

    def snapshot():
        return {
            model: sorted(getattr(obj, pk) for obj in model.objects.all())
            for model, pk in keyed
        }

    ids_before = snapshot()
    scheme_fields = {s.id: (s.name, s.rules) for s in Scheme.objects.all()}

    _out, err = run_import()  # second run
    assert_counts()

    assert snapshot() == ids_before
    assert {s.id: (s.name, s.rules) for s in Scheme.objects.all()} == scheme_fields
    # kn-missing warnings are reported again on every run (loader behaviour).
    assert "Kannada copy pending" in err.getvalue()


@pytest.mark.django_db
def test_invalid_data_aborts_with_zero_writes(tmp_path):
    # The session may already hold imported rows (endpoint tests import
    # session-wide), so clear the content tables first: after the failed
    # import they must still be empty.
    Scheme.objects.all().delete()
    Question.objects.all().delete()
    Reason.objects.all().delete()
    Fix.objects.all().delete()
    IncomeBucket.objects.all().delete()
    CscCenter.objects.all().delete()
    PincodeCentroid.objects.all().delete()

    broken = tmp_path / "data"
    broken.mkdir()
    # Copy the 7 real files, then break one: unknown reason code.
    for name in ("schemes.json", "questions.json", "reasons.json", "fixes.json",
                 "income-buckets.json"):
        (broken / name).write_bytes((REPO_DATA / name).read_bytes())
    (broken / "csc").mkdir()
    (broken / "csc" / "mysuru.json").write_bytes((REPO_DATA / "csc" / "mysuru.json").read_bytes())
    (broken / "csc" / "pincodes_mysuru.json").write_bytes(
        (REPO_DATA / "csc" / "pincodes_mysuru.json").read_bytes()
    )
    schemes = json.loads((broken / "schemes.json").read_text(encoding="utf-8"))
    schemes["schemes"][0]["rules"] = {
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
    (broken / "schemes.json").write_text(json.dumps(schemes), encoding="utf-8")

    with pytest.raises(CommandError) as exc:
        run_import(broken)
    assert "reason.bogus" in str(exc.value)
    assert Scheme.objects.count() == 0
    assert Question.objects.count() == 0
    assert Reason.objects.count() == 0
    assert Fix.objects.count() == 0
    assert IncomeBucket.objects.count() == 0
    assert CscCenter.objects.count() == 0
    assert PincodeCentroid.objects.count() == 0


@pytest.mark.django_db
def test_missing_data_dir_errors(tmp_path):
    with pytest.raises(CommandError):
        run_import(tmp_path / "no-such-dir")
