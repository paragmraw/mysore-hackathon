from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.schemes.engine.contract import (
    Check,
    FixDef,
    ReasonDef,
    ReasonRef,
    SchemeRecord,
)
from apps.schemes.serializers import loc_out, render_fix, render_reason

# Outcomes of a single check.
PASS = "pass"
FAIL = "fail"
MISSING = "missing"

INCOME_FIELD = "income"

POSTMATRIC_ROUTES = {
    "sc": "postmatric-sc",
    "obc": "postmatric-obc-bcwd",
    "minority": "postmatric-minority",
    "st": "postmatric-tribal",
}
VEHICLE_ROUTES = {
    "st": "swavalambi-adcl",
    "minority": "swavalambi-kmdc",
}
ROUTE_FIELD = "category"


@dataclass(frozen=True)
class EvalContext:
    optional_ids: frozenset[str]
    reasons: dict[str, ReasonDef]
    fixes: dict[str, FixDef]
    income_buckets: dict[str, dict[str, Any]]


def route_value(group: str, answers: dict[str, Any]) -> str | None:
    category = answers.get(ROUTE_FIELD)
    if not category:
        return None
    category = str(category)
    if group == "postmatric":
        return POSTMATRIC_ROUTES.get(category)
    if group == "vehicle":
        return VEHICLE_ROUTES.get(category)
    return None


def _unanswered(value: Any) -> bool:
    return value is None or value == ""


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def check_outcome(
    check: Check,
    answers: dict[str, Any],
    ctx: EvalContext,
    *,
    skip_missing_optional: bool = False,
) -> str:
    if check.op == "income_lte":
        raw = answers.get(INCOME_FIELD)
        if _unanswered(raw):
            return PASS if (INCOME_FIELD in ctx.optional_ids and not skip_missing_optional) else MISSING
        bucket = ctx.income_buckets.get(str(raw))
        if bucket is None:
            return MISSING
        upper = bucket.get("upper")
        return PASS if upper is not None and upper <= check.value else FAIL

    field = check.field
    raw = answers.get(field)
    if _unanswered(raw):
        if field in ctx.optional_ids:
            return MISSING if skip_missing_optional else PASS
        return MISSING

    if check.op == "equals":
        return PASS if raw == check.value else FAIL
    if check.op == "in":
        return PASS if raw in (check.values or []) else FAIL
    if check.op in ("num_gte", "num_lte"):
        number = _as_number(raw)
        if number is None:
            return MISSING
        bound = _as_number(check.value)
        if bound is None:
            return MISSING
        return PASS if (number >= bound if check.op == "num_gte" else number <= bound) else FAIL
    raise ValueError(f"Unknown check op: {check.op!r}")


def _fmt_answer(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _result(
    scheme: SchemeRecord,
    locale: str,
    status: str,
    reasons: list[dict[str, Any]],
    fixes: list[dict[str, Any]],
    facts: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "scheme_id": scheme.id,
        "code": scheme.code,
        "name": loc_out(scheme.name, locale),
        "summ": loc_out(scheme.summ, locale),
        "status": status,
        "confidence": "likely",
        "reasons": reasons,
        "fixes": fixes,
        "matched_facts": facts,
        "docs": [loc_out(doc, locale) for doc in scheme.docs],
    }


def evaluate_scheme(
    scheme: SchemeRecord,
    answers: dict[str, Any],
    ctx: EvalContext,
    locale: str = "en",
    lenient: bool = False,
) -> dict[str, Any]:
    reasons: list[dict[str, Any]] = []
    fixes: list[dict[str, Any]] = []
    for rule in scheme.rules.exclusions:
        outcome = check_outcome(rule.check, answers, ctx, skip_missing_optional=True)
        if outcome == PASS:
            reasons.append(render_reason(rule.reason, ctx.reasons, locale))
            return _result(scheme, locale, "not_eligible", reasons, fixes, [])
    blocked = False
    facts_with_id: list[tuple[str, dict[str, str]]] = []
    for rule in scheme.rules.eligibility:
        outcome = check_outcome(rule.check, answers, ctx)
        if outcome == MISSING:
            if lenient:
                continue
            reasons.append(
                render_reason(ReasonRef(code="reason.infoMissing"), ctx.reasons, locale)
            )
            facts = [fact for _, fact in sorted(facts_with_id, key=lambda pair: pair[0])][:6]
            return _result(scheme, locale, "not_eligible", reasons, fixes, facts)
        if rule.on_fail.status == "blocked":
            if outcome == PASS:
                blocked = True
                reasons.append(render_reason(rule.on_fail.reason, ctx.reasons, locale))
                fixes.append(
                    render_fix(
                        rule.on_fail.fix_id, rule.on_fail.reason, ctx.fixes, ctx.reasons, locale
                    )
                )
            continue
        if outcome == FAIL:
            reasons.append(render_reason(rule.on_fail.reason, ctx.reasons, locale))
            facts = [fact for _, fact in sorted(facts_with_id, key=lambda pair: pair[0])][:6]
            return _result(scheme, locale, "not_eligible", reasons, fixes, facts)
        if rule.check.op in ("equals", "in"):
            facts_with_id.append(
                (
                    rule.id,
                    {
                        "question_id": rule.check.field,
                        "answer": _fmt_answer(answers.get(rule.check.field)),
                    },
                )
            )

    for rule in scheme.rules.fixes:
        outcome = check_outcome(rule.check, answers, ctx, skip_missing_optional=True)
        if outcome == PASS:
            blocked = True
            reasons.append(render_reason(rule.reason, ctx.reasons, locale))
            fixes.append(render_fix(rule.fix_id, rule.reason, ctx.fixes, ctx.reasons, locale))

    facts = [fact for _, fact in sorted(facts_with_id, key=lambda pair: pair[0])][:6]
    status = "blocked" if blocked else "eligible"
    return _result(scheme, locale, status, reasons, fixes, facts)


def deep_check_scheme(
    scheme: SchemeRecord,
    base_answers: dict[str, Any],
    deep_answers: dict[str, Any],
    ctx: EvalContext,
    locale: str = "en",
) -> dict[str, Any]:
    base = evaluate_scheme(scheme, base_answers, ctx, locale)
    if base["status"] == "not_eligible":
        return base
    reasons = list(base["reasons"])
    fixes = list(base["fixes"])
    blocked = base["status"] == "blocked"
    for rule in scheme.rules.deep_check:
        outcome = check_outcome(rule.check, deep_answers, ctx, skip_missing_optional=True)
        if outcome == PASS:
            blocked = True
            reasons.append(render_reason(rule.reason, ctx.reasons, locale))
            fixes.append(render_fix(rule.fix_id, rule.reason, ctx.fixes, ctx.reasons, locale))
    return _result(
        scheme, locale, "blocked" if blocked else "eligible", reasons, fixes, base["matched_facts"]
    )


def match_schemes(
    schemes: list[SchemeRecord],
    answers: dict[str, Any],
    ctx: EvalContext,
    locale: str = "en",
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    hidden_groups: set[str] = set()
    for scheme in schemes:
        if scheme.route is not None:
            raw_category = answers.get(ROUTE_FIELD)
            routed = route_value(scheme.route.group, answers) == scheme.route.value
            raw_match = raw_category is not None and str(raw_category) == scheme.route.value
            if not (routed or raw_match):
                hidden_groups.add(scheme.route.group)
                continue
        results.append(evaluate_scheme(scheme, answers, ctx, locale))
    return {"results": results, "hidden_route_groups": sorted(hidden_groups)}


def quick_match_schemes(
    schemes: list[SchemeRecord],
    answers: dict[str, Any],
    ctx: EvalContext,
    locale: str = "en",
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    hidden_groups: set[str] = set()
    for scheme in schemes:
        if scheme.route is not None:
            raw_category = answers.get(ROUTE_FIELD)
            routed = route_value(scheme.route.group, answers) == scheme.route.value
            raw_match = raw_category is not None and str(raw_category) == scheme.route.value
            if not (routed or raw_match):
                hidden_groups.add(scheme.route.group)
                continue
        result = evaluate_scheme(scheme, answers, ctx, locale, lenient=True)
        if result["status"] != "not_eligible":
            results.append(result)
    return {"results": results, "hidden_route_groups": sorted(hidden_groups)}
