"""Bundle build + signal-driven cache invalidation."""

import pytest

from apps.schemes import bundle as bundle_module
from apps.schemes.bundle import build, get_bundle, reset_bundle
from apps.schemes.models import Reason

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_bundle()
    yield
    reset_bundle()


def test_build_from_imported_data(imported):
    bundle = build(force=True)
    assert len(bundle.schemes) == 19
    assert len(bundle.schemes_raw) == 19
    assert [s.id for s in bundle.schemes] == [raw["id"] for raw in bundle.schemes_raw]
    assert bundle.schemes_by_id["gruha-lakshmi"].code == "GLK"
    assert bundle.questions_by_id["bank"].cols == 2
    assert bundle.optional_ids == frozenset(["disability", "pincode"])
    assert "reason.infoMissing" in bundle.reasons
    assert "bank-aadhaar-link" in bundle.fixes
    assert bundle.income_buckets["gt-8l"]["upper"] is None
    assert [c.id for c in bundle.csc_centers] == sorted(c.id for c in bundle.csc_centers)
    assert bundle.csc_centroids["570001"]["lat"]
    assert bundle.last_data_update == max(
        raw["last_verified"] for raw in bundle.schemes_raw
    )


def test_new_fields_round_trip(imported):
    """amount_inr/amount_period, question stage/scheme_id, and deep_check rules
    survive the DB round trip into the bundle."""
    bundle = build(force=True)

    gl = bundle.schemes_by_id["gruha-lakshmi"]
    assert gl.amount_inr == 2000
    assert gl.amount_period == "month"
    assert gl.rules.deep_check  # every scheme carries deep-check rules
    assert all(r.fix_id for r in gl.rules.deep_check)
    assert all(r.reason.code.startswith("reason.dc") for r in gl.rules.deep_check)

    pm_kisan = bundle.schemes_by_id["pm-kisan"]
    assert pm_kisan.amount_inr == 6000
    assert pm_kisan.amount_period == "year"

    yn = bundle.schemes_by_id["yuva-nidhi"]
    assert any(r.id == "yn-e-emp" for r in yn.rules.eligibility)

    # Raw dicts carry the same values (bundle._scheme_raw round trip).
    gl_raw = next(raw for raw in bundle.schemes_raw if raw["id"] == "gruha-lakshmi")
    assert gl_raw["amount_inr"] == 2000
    assert gl_raw["amount_period"] == "month"
    assert gl_raw["rules"]["deep_check"]

    # Question stage/scheme_id.
    assert bundle.questions_by_id["age"].stage == ["quick", "full"]
    assert bundle.questions_by_id["employment"].stage == ["quick", "full"]
    assert bundle.questions_by_id["pincode"].stage == ["full"]
    assert bundle.questions_by_id["dc_ration_head"].stage == ["deep"]
    assert bundle.questions_by_id["dc_ration_head"].scheme_id == "gruha-lakshmi"
    assert bundle.questions_by_id["dc_aadhaar_name_match"].scheme_id is None


def test_get_bundle_is_memoized(imported):
    first = get_bundle()
    assert get_bundle() is first
    assert build(force=True) is not first


def test_post_save_invalidates_cache(imported):
    get_bundle()  # warm the cache
    assert bundle_module._BUNDLE is not None

    reason = Reason.objects.get(code="reason.infoMissing")
    reason.message = {"en": "changed", "kn": "changed"}
    reason.save()

    # post_save dropped the cached bundle; the next build sees the new row.
    assert bundle_module._BUNDLE is None
    fresh = get_bundle()
    assert fresh.reasons["reason.infoMissing"].message.en == "changed"

    reason.delete()
    assert bundle_module._BUNDLE is None
    fresh = get_bundle()
    assert "reason.infoMissing" not in fresh.reasons
