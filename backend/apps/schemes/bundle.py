from __future__ import annotations

from apps.csc.models import CscCenter as CscCenterModel
from apps.csc.models import PincodeCentroid
from apps.schemes.engine import contract
from apps.schemes.engine.contract import (
    CscCenter,
    DataBundle,
    FixDef,
    Question,
    ReasonDef,
    Rules,
    SchemeRecord,
)
from apps.schemes.models import Fix, IncomeBucket, Question as QuestionModel
from apps.schemes.models import Reason, Scheme

_BUNDLE: DataBundle | None = None


def _scheme_raw(row: Scheme) -> dict:
    return {
        "id": row.id,
        "code": row.code,
        "name": dict(row.name),
        "summ": dict(row.summ),
        "department": dict(row.department),
        "benefit_type": row.benefit_type,
        "jurisdiction": row.jurisdiction,
        "benefit": dict(row.benefit),
        "amount": dict(row.amount),
        "amount_inr": row.amount_inr,
        "amount_period": row.amount_period,
        "deadline": dict(row.deadline),
        "eligibility_criteria": [dict(item) for item in row.eligibility_criteria],
        "application_steps": [dict(item) for item in row.application_steps],
        "channels": [dict(channel) for channel in row.channels],
        "docs": [dict(item) for item in row.docs],
        "route": row.route,
        "criteria_note": row.criteria_note,
        "rules": contract.Rules.model_validate(row.rules).model_dump(exclude_none=True),
        "confidence_note": row.confidence_note,
        "last_verified": row.last_verified.isoformat(),
        "source_url": row.source_url,
        "source_note": dict(row.source_note),
    }


def _question_raw(row: QuestionModel) -> dict:
    return {
        "id": row.id,
        "type": row.type,
        "label": dict(row.label),
        "options": row.options,
        "cols": row.cols,
        "optional": row.optional,
        "show_if": row.show_if,
        "stage": row.stage,
        "scheme_id": row.scheme_id,
    }


def build(force: bool = False) -> DataBundle:
    global _BUNDLE
    if _BUNDLE is not None and not force:
        return _BUNDLE

    schemes_raw = [_scheme_raw(row) for row in Scheme.objects.order_by("order")]
    questions_raw = [_question_raw(row) for row in QuestionModel.objects.order_by("order")]

    reasons = {
        row.code: ReasonDef.model_validate({"message": row.message})
        for row in Reason.objects.order_by("code")
    }
    fixes = {
        row.id: FixDef.model_validate({"title": row.title, "steps": row.steps})
        for row in Fix.objects.order_by("id")
    }
    income_buckets = {
        row.id: {"min": row.min, "upper": row.upper}
        for row in IncomeBucket.objects.order_by("order")
    }
    csc_centers = [
        CscCenter.model_validate(
            {
                "id": row.id,
                "name": dict(row.name),
                "address": dict(row.address),
                "locality": row.locality,
                "city": row.city,
                "taluk": row.taluk,
                "pincode": row.pincode,
                "lat": row.lat,
                "lng": row.lng,
                "phone": row.phone,
                "hours": row.hours,
            }
        )
        for row in CscCenterModel.objects.order_by("id")
    ]
    csc_centroids = {
        row.pincode: {"lat": row.lat, "lng": row.lng}
        for row in PincodeCentroid.objects.order_by("pincode")
    }

    _BUNDLE = DataBundle(
        schemes=[SchemeRecord.model_validate(raw) for raw in schemes_raw],
        schemes_raw=schemes_raw,
        questions=[Question.model_validate(raw) for raw in questions_raw],
        reasons=reasons,
        fixes=fixes,
        income_buckets=income_buckets,
        csc_centers=csc_centers,
        csc_centroids=csc_centroids,
    )
    return _BUNDLE


def get_bundle() -> DataBundle:
    return build()


def reset_bundle() -> None:
    global _BUNDLE
    _BUNDLE = None


def _invalidate(sender=None, **_kwargs) -> None:
    global _BUNDLE
    _BUNDLE = None


def connect_signals() -> None:
    from django.db.models.signals import post_delete, post_save

    for model in (Scheme, QuestionModel, Reason, Fix, IncomeBucket, CscCenterModel, PincodeCentroid):
        dispatch_uid = f"bundle-invalidate-{model._meta.label}"
        post_save.connect(_invalidate, sender=model, dispatch_uid=dispatch_uid, weak=False)
        post_delete.connect(_invalidate, sender=model, dispatch_uid=dispatch_uid, weak=False)
