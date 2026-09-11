from __future__ import annotations

from typing import Any

from apps.schemes.engine.contract import (
    FixDef,
    Localized,
    ReasonDef,
    ReasonRef,
    SchemeRecord,
)


def loc_out(obj: Localized, locale: str = "en") -> dict[str, str]:
    en = obj.en or ""
    kn = obj.kn or en
    if locale == "kn" and kn:
        return {"en": en, "kn": kn}
    return {"en": en, "kn": kn}


def _substitute(message: str, params: dict[str, str] | None) -> str:
    if not params:
        return message
    out = message
    for key, value in params.items():
        out = out.replace("{" + key + "}", str(value))
    return out


def render_reason(
    ref: ReasonRef, reasons: dict[str, ReasonDef], locale: str = "en"
) -> dict[str, Any]:
    spec = reasons.get(ref.code)
    if spec is None:
        en = kn = ref.code
    else:
        en = spec.message.en or ref.code
        kn = spec.message.kn or en
    en, kn = _substitute(en, ref.params), _substitute(kn, ref.params)
    out: dict[str, Any] = {"code": ref.code, "message": {"en": en, "kn": kn}}
    if ref.params:
        out["params"] = dict(ref.params)
    return out


def render_fix(
    fix_id: str,
    reason: ReasonRef,
    fixes: dict[str, FixDef],
    reasons: dict[str, ReasonDef],
    locale: str = "en",
) -> dict[str, Any]:
    spec = fixes.get(fix_id)
    title = spec.title if spec is not None else Localized(en=fix_id)
    steps = spec.steps if spec is not None else []
    return {
        "fix_id": fix_id,
        "reason": render_reason(reason, reasons, locale),
        "title": loc_out(title, locale),
        "steps": [loc_out(s, locale) for s in steps],
    }

def question_out(q, locale: str = "en") -> dict:
    item: dict = {"id": q.id, "type": q.type, "label": loc_out(q.label, locale)}
    if q.options:
        item["options"] = [
            {"value": option.value, "label": loc_out(option.label, locale)}
            for option in q.options
        ]
    if q.cols is not None:
        item["cols"] = q.cols
    if q.optional:
        item["optional"] = True
    if q.show_if is not None:
        item["showIf"] = q.show_if
    return item


def quick_match_result_out(scheme, raw, locale="en") -> dict:
    return {
        "scheme_id": scheme.id,
        "code": scheme.code,
        "name": loc_out(scheme.name, locale),
        "summ": loc_out(scheme.summ, locale),
        "status": "likely",
        "confidence": "likely",
        "amount_inr": scheme.amount_inr,
        "amount_period": scheme.amount_period,
        "amount": loc_out(scheme.amount, locale),
    }


def _channel_out(channel, locale: str) -> dict:
    if channel.type == "portal":
        return {"type": "portal", "label": loc_out(channel.label, locale), "url": channel.url}
    return {"type": "csc"}


def scheme_out(scheme: SchemeRecord, raw: dict, locale: str) -> dict:
    route = raw.get("route")
    return {
        "id": scheme.id,
        "code": scheme.code,
        "name": loc_out(scheme.name, locale),
        "summ": loc_out(scheme.summ, locale),
        "department": loc_out(scheme.department, locale),
        "benefit_type": scheme.benefit_type,
        "jurisdiction": scheme.jurisdiction,
        "benefit": loc_out(scheme.benefit, locale),
        "amount": loc_out(scheme.amount, locale),
        "amount_inr": scheme.amount_inr,
        "amount_period": scheme.amount_period,
        "deadline": loc_out(scheme.deadline, locale),
        "eligibility_criteria": [loc_out(item, locale) for item in scheme.eligibility_criteria],
        "application_steps": [loc_out(item, locale) for item in scheme.application_steps],
        "channels": [_channel_out(channel, locale) for channel in scheme.channels],
        "docs": [loc_out(item, locale) for item in scheme.docs],
        "route": route,
        "criteria_note": loc_out(scheme.criteria_note, locale) if scheme.criteria_note else None,
        "rules": raw.get("rules", {"eligibility": [], "exclusions": [], "fixes": []}),
        "confidence_note": scheme.confidence_note,
        "last_verified": scheme.last_verified,
        "source_url": scheme.source_url,
        "source_note": loc_out(scheme.source_note, locale),
    }
