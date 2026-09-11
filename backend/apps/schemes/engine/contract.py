from __future__ import annotations

from typing import Any, Iterator

from pydantic import BaseModel, ConfigDict, Field

class Localized(BaseModel):

    model_config = ConfigDict(extra="allow")

    en: str
    kn: str | None = None


class ReasonRef(BaseModel):
    code: str
    params: dict[str, str] | None = None


class Check(BaseModel):
    model_config = ConfigDict(extra="allow")

    op: str
    field: str | None = None
    value: Any = None
    values: list[Any] | None = None


class OnFail(BaseModel):
    status: str  # "blocked" | "not_eligible"
    reason: ReasonRef
    fix_id: str | None = None


class EligibilityRule(BaseModel):
    id: str
    check: Check
    on_fail: OnFail


class ExclusionRule(BaseModel):
    id: str
    check: Check
    reason: ReasonRef


class FixRule(BaseModel):
    id: str
    check: Check
    reason: ReasonRef
    fix_id: str


class Rules(BaseModel):
    eligibility: list[EligibilityRule] = []
    exclusions: list[ExclusionRule] = []
    fixes: list[FixRule] = []
    deep_check: list[FixRule] = []


class Route(BaseModel):
    group: str
    value: str


class Channel(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    label: Localized | None = None
    url: str | None = None


class SchemeRecord(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    code: str = ""
    name: Localized
    summ: Localized = Localized(en="")
    department: Localized = Localized(en="")
    benefit_type: str = ""
    jurisdiction: str = ""
    benefit: Localized = Localized(en="")
    amount: Localized = Localized(en="")
    amount_inr: float | None = None
    amount_period: str = ""
    deadline: Localized = Localized(en="")
    eligibility_criteria: list[Localized] = []
    application_steps: list[Localized] = []
    channels: list[Channel] = []
    docs: list[Localized] = []
    route: Route | None = None
    criteria_note: Localized | None = None
    rules: Rules = Rules()
    confidence_note: str = ""
    last_verified: str = ""
    source_url: str = ""
    source_note: Localized = Localized(en="")


class QuestionOption(BaseModel):
    value: str
    label: Localized


class Question(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    type: str 
    label: Localized
    options: list[QuestionOption] | None = None
    cols: int | None = None
    optional: bool = False
    show_if: dict[str, Any] | None = Field(default=None, alias="showIf")
    stage: list[str] = ["full"]
    scheme_id: str | None = None


class ReasonDef(BaseModel):
    message: Localized


class FixDef(BaseModel):
    title: Localized
    steps: list[Localized] = []


class CscCenter(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    name: Localized
    address: Localized
    locality: str = ""
    city: str = ""
    taluk: str = ""
    pincode: str = ""
    lat: float
    lng: float
    phone: str | None = None
    hours: str | None = None


class DataError(Exception):
    """Raised when contract data fails validation."""


class DataBundle:

    def __init__(
        self,
        *,
        schemes: list[SchemeRecord],
        schemes_raw: list[dict[str, Any]],
        questions: list[Question],
        reasons: dict[str, ReasonDef],
        fixes: dict[str, FixDef],
        income_buckets: dict[str, dict[str, Any]],
        csc_centers: list[CscCenter],
        csc_centroids: dict[str, dict[str, float]],
    ) -> None:
        self.schemes = schemes
        self.schemes_raw = schemes_raw
        self.questions = questions
        self.reasons = reasons
        self.fixes = fixes
        self.income_buckets = income_buckets
        self.csc_centers = csc_centers
        self.csc_centroids = csc_centroids
        self.schemes_by_id = {s.id: s for s in schemes}
        self.questions_by_id = {q.id: q for q in questions}
        self.optional_ids = frozenset(q.id for q in questions if q.optional)

    @property
    def last_data_update(self) -> str:
        return max((s.last_verified for s in self.schemes), default="")

def loc(obj: Localized | dict[str, Any], locale: str = "en") -> str:
    """``obj[locale]`` with fallback to ``en``."""
    if isinstance(obj, Localized):
        en, kn = obj.en, obj.kn
    else:
        en, kn = obj.get("en"), obj.get("kn")
    if locale == "kn" and kn:
        return kn
    return en or ""


def loc_out(obj: Localized, locale: str = "en") -> dict[str, str]:
    """Localized object as an ``{en, kn}`` dict with kn falling back to en."""
    en = obj.en or ""
    kn = obj.kn or en
    return {"en": en, "kn": kn}

_KNOWN_OPS = {"equals", "in", "num_gte", "num_lte", "income_lte"}
_ROUTE_GROUPS = {"postmatric", "vehicle"}
_ROUTE_VALUES = {
    "postmatric": {
        "postmatric-sc", "postmatric-obc-bcwd", "postmatric-minority", "postmatric-tribal",
        "sc", "obc", "minority", "st",
    },
    "vehicle": {"swavalambi-adcl", "swavalambi-kmdc", "st", "minority"},
}
_INCOME_FIELD = "income"


def _iter_localized(obj: Any, path: str) -> Iterator[tuple[dict[str, Any], str]]:
    if isinstance(obj, dict):
        if obj and set(obj) <= {"en", "kn"} and all(isinstance(v, str) for v in obj.values()):
            yield obj, path
            return
        for key, value in obj.items():
            yield from _iter_localized(value, f"{path}.{key}")
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            yield from _iter_localized(value, f"{path}[{index}]")


def check_rule(check: Check, question_ids: set[str] | None) -> list[str]:
    errors: list[str] = []
    if check.op not in _KNOWN_OPS:
        return [f"unknown check op '{check.op}'"]
    if check.op == "income_lte":
        if check.field is not None:
            errors.append("op 'income_lte' takes no field")
        if not isinstance(check.value, (int, float)) or isinstance(check.value, bool):
            errors.append("op 'income_lte' needs a numeric value")
    else:
        if not check.field:
            errors.append(f"op '{check.op}' requires a field")
        elif question_ids is not None and check.field not in question_ids:
            errors.append(f"check field '{check.field}' is not a question id")
    if check.op == "in" and not check.values:
        errors.append("op 'in' requires a non-empty 'values' list")
    if check.op in ("num_gte", "num_lte") and (
        not isinstance(check.value, (int, float)) or isinstance(check.value, bool)
    ):
        errors.append(f"op '{check.op}' needs a numeric value")
    return errors


def validate_bundle(
    bundle: DataBundle,
    schemes_raw: list[dict[str, Any]],
    questions_raw: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    question_ids = set(bundle.questions_by_id)

    # Duplicate scheme ids.
    seen: set[str] = set()
    for scheme in bundle.schemes:
        if scheme.id in seen:
            errors.append(f"duplicate scheme id: {scheme.id}")
        seen.add(scheme.id)
        if not scheme.last_verified:
            errors.append(f"scheme {scheme.id}: 'last_verified' is missing")
        if scheme.route is not None:
            if scheme.route.group not in _ROUTE_GROUPS:
                errors.append(
                    f"scheme {scheme.id}: route group '{scheme.route.group}' not in {sorted(_ROUTE_GROUPS)}"
                )
            elif scheme.route.value not in _ROUTE_VALUES[scheme.route.group]:
                warnings.append(
                    f"scheme {scheme.id}: route value '{scheme.route.value}' "
                    f"is not a known routed value for group '{scheme.route.group}'"
                )

    missing_en = 0
    missing_kn = 0
    equal_kn = 0
    sample_paths: list[str] = []
    for source, label in ((schemes_raw, "schemes"), (questions_raw, "questions")):
        for localized, path in _iter_localized(source, label):
            if not localized.get("en"):
                missing_en += 1
                if len(sample_paths) < 5:
                    sample_paths.append(f"{path} (missing en)")
            elif "kn" not in localized or not localized["kn"]:
                missing_kn += 1
            elif localized["kn"] == localized["en"]:
                equal_kn += 1
    if missing_en:
        errors.append(
            f"{missing_en} localized strings are missing 'en' (first: {sample_paths})"
            if sample_paths
            else f"{missing_en} localized strings are missing 'en'"
        )
    if missing_kn or equal_kn:
        warnings.append(
            f"Kannada copy pending: {missing_kn} localized strings have no 'kn' "
            f"and {equal_kn} have kn == en"
        )

    _KNOWN_STAGES = {"quick", "full", "deep"}
    for question in bundle.questions:
        for stage in question.stage:
            if stage not in _KNOWN_STAGES:
                errors.append(f"question {question.id}: invalid stage '{stage}'")
        if question.scheme_id is not None and "deep" not in question.stage:
            errors.append(
                f"question {question.id}: scheme_id set on a non-deep question"
            )
        if question.scheme_id is not None and question.scheme_id not in bundle.schemes_by_id:
            errors.append(
                f"question {question.id}: unknown scheme_id '{question.scheme_id}'"
            )

    for scheme in bundle.schemes:
        all_rules: list[tuple[str, Check, list[ReasonRef], list[str]]] = [
            ("eligibility", r.check, [r.on_fail.reason], [r.on_fail.fix_id] if r.on_fail.fix_id else [])
            for r in scheme.rules.eligibility
        ]
        all_rules += [("exclusion", r.check, [r.reason], []) for r in scheme.rules.exclusions]
        all_rules += [("fix", r.check, [r.reason], [r.fix_id]) for r in scheme.rules.fixes]
        all_rules += [("deep_check", r.check, [r.reason], [r.fix_id]) for r in scheme.rules.deep_check]

        for kind, check, reason_refs, fix_ids in all_rules:
            errors.extend(
                f"scheme {scheme.id}: {error}" for error in check_rule(check, question_ids)
            )

            for ref in reason_refs:
                if ref.code not in bundle.reasons:
                    errors.append(f"scheme {scheme.id}: unknown reason code '{ref.code}'")
            for fix_id in fix_ids:
                if fix_id not in bundle.fixes:
                    errors.append(f"scheme {scheme.id}: unknown fix_id '{fix_id}'")

    if _INCOME_FIELD not in bundle.questions_by_id:
        errors.append(f"op 'income_lte' requires the '{_INCOME_FIELD}' question")

    quick_ids = {q.id for q in bundle.questions if "quick" in q.stage}
    for required in ("age", "income", "employment"):
        if required not in quick_ids:
            warnings.append(f"quick stage lacks the '{required}' question")

    return errors, warnings
