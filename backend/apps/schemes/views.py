from django.http import JsonResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.accounts.views import SessionApiView
from apps.schemes.bundle import get_bundle
from apps.schemes.engine.evaluator import (
    EvalContext,
    deep_check_scheme,
    match_schemes,
    quick_match_schemes,
)
from apps.schemes.serializers import (
    question_out,
    quick_match_result_out,
    scheme_out,
)

_VALID_LOCALES = ("en", "kn")


def _locale_or_error(request):
    locale = request.query_params.get("locale", "en")
    if locale not in _VALID_LOCALES:
        return None, JsonResponse(
            {"detail": "locale must be one of: en, kn"}, status=422
        )
    return locale, None


def health(request):
    return JsonResponse({"status": "ok"})


class MetaView(APIView):

    def get(self, request):
        bundle = get_bundle()
        return Response(
            {
                "schemes": len(bundle.schemes),
                "questions": len(bundle.questions),
                "last_data_update": bundle.last_data_update,
            }
        )


class QuestionsView(APIView):

    def get(self, request):
        locale, error = _locale_or_error(request)
        if error:
            return error
        stage = request.query_params.get("stage", "full")
        if stage not in ("quick", "full", "deep"):
            return JsonResponse(
                {"detail": "stage must be one of: quick, full, deep"}, status=422
            )
        scheme_id = request.query_params.get("scheme_id")
        bundle = get_bundle()
        if stage == "deep" and scheme_id is not None and scheme_id not in bundle.schemes_by_id:
            raise NotFound(detail=f"Unknown scheme: {scheme_id}")
        if stage == "deep":
            questions = [
                q
                for q in bundle.questions
                if "deep" in q.stage and (q.scheme_id is None or q.scheme_id == scheme_id)
            ]
        else:
            questions = [q for q in bundle.questions if stage in q.stage]
        return Response([question_out(q, locale) for q in questions])


class SchemesView(APIView):

    def get(self, request):
        locale, error = _locale_or_error(request)
        if error:
            return error
        bundle = get_bundle()
        return Response(
            [
                scheme_out(scheme, raw, locale)
                for scheme, raw in zip(bundle.schemes, bundle.schemes_raw)
            ]
        )


class SchemeDetailView(APIView):

    def get(self, request, scheme_id: str):
        locale, error = _locale_or_error(request)
        if error:
            return error
        bundle = get_bundle()
        scheme = bundle.schemes_by_id.get(scheme_id)
        if scheme is None:
            raise NotFound(detail=f"Unknown scheme: {scheme_id}")
        index = bundle.schemes.index(scheme)
        return Response(scheme_out(scheme, bundle.schemes_raw[index], locale))

class _ParityHTTPError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _normalize_answers(answers: dict, bundle) -> dict:
    normalized: dict = {}
    for key, value in answers.items():
        question = bundle.questions_by_id.get(key)
        if question is None:
            raise _ParityHTTPError(
                422,
                f"Unknown answer key '{key}': not a question id.",
            )
        if value is None:
            normalized[key] = None
            continue
        if question.type == "number":
            if isinstance(value, bool):
                raise _ParityHTTPError(422, f"Answer for '{key}' must be a number.")
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise _ParityHTTPError(422, f"Answer for '{key}' must be a number.")
            normalized[key] = int(number) if number.is_integer() else number
        elif question.type == "pincode":
            text = str(value)
            if not (text.isdigit() and len(text) == 6):
                raise _ParityHTTPError(
                    422,
                    f"Answer for '{key}' must be a 6-digit pincode.",
                )
            normalized[key] = text
        else: 
            allowed = {option.value for option in question.options or []}
            if str(value) not in allowed:
                raise _ParityHTTPError(
                    422,
                    f"Invalid value '{value}' for question '{key}'.",
                )
            normalized[key] = str(value)
    return normalized


class MatchView(APIView):
    def post(self, request):
        body = request.data if isinstance(request.data, dict) else {}
        # locale parity: FastAPI's Literal["en", "kn"] body field (default "en").
        locale = body.get("locale", "en")
        if locale not in _VALID_LOCALES:
            return JsonResponse(
                {"detail": "locale must be one of: en, kn"}, status=422
            )
        answers = body.get("answers", {})
        if not isinstance(answers, dict):
            return JsonResponse(
                {"detail": "answers must be an object"}, status=422
            )

        bundle = get_bundle()
        try:
            normalized = _normalize_answers(answers, bundle)
        except _ParityHTTPError as exc:
            return JsonResponse({"detail": exc.detail}, status=exc.status_code)

        ctx = EvalContext(
            optional_ids=bundle.optional_ids,
            reasons=bundle.reasons,
            fixes=bundle.fixes,
            income_buckets=bundle.income_buckets,
        )
        return Response(match_schemes(bundle.schemes, normalized, ctx, locale))

class QuickMatchView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        body = request.data if isinstance(request.data, dict) else {}
        locale = body.get("locale", "en")
        if locale not in _VALID_LOCALES:
            return JsonResponse(
                {"detail": "locale must be one of: en, kn"}, status=422
            )
        answers = body.get("answers", {})
        if not isinstance(answers, dict):
            return JsonResponse(
                {"detail": "answers must be an object"}, status=422
            )
        for field in ("age", "income", "employment"):
            if field not in answers:
                return JsonResponse(
                    {"detail": "answers must include age, income and employment"},
                    status=422,
                )

        bundle = get_bundle()
        try:
            normalized = _normalize_answers(answers, bundle)
        except _ParityHTTPError as exc:
            return JsonResponse({"detail": exc.detail}, status=exc.status_code)

        ctx = EvalContext(
            optional_ids=bundle.optional_ids,
            reasons=bundle.reasons,
            fixes=bundle.fixes,
            income_buckets=bundle.income_buckets,
        )
        raw = quick_match_schemes(bundle.schemes, normalized, ctx, locale)
        results = [
            quick_match_result_out(bundle.schemes_by_id[item["scheme_id"]], item, locale)
            for item in raw["results"]
        ]
        benefit_total = {"month": 0, "one-time": 0, "year": 0}
        for item in results:
            amount = item["amount_inr"]
            if amount is None:
                continue
            period = item["amount_period"]
            if period in benefit_total:
                benefit_total[period] += amount
        return Response(
            {
                "results": results,
                "benefit_total": benefit_total,
                "hidden_route_groups": raw["hidden_route_groups"],
            }
        )

class DeepCheckView(SessionApiView):

    permission_classes = [IsAuthenticated]

    def get_authenticate_header(self, request):
        return "Session"

    def post(self, request):
        profile = getattr(request.user, "profile", None)
        if profile is None or not profile.answers:
            return JsonResponse(
                {"detail": "Complete the questionnaire before a deep check."},
                status=400,
            )
        body = request.data if isinstance(request.data, dict) else {}
        locale = body.get("locale", "en")
        if locale not in _VALID_LOCALES:
            return JsonResponse(
                {"detail": "locale must be one of: en, kn"}, status=422
            )
        scheme_id = body.get("scheme_id")
        bundle = get_bundle()
        scheme = bundle.schemes_by_id.get(scheme_id)
        if scheme is None:
            raise NotFound(detail=f"Unknown scheme: {scheme_id}")
        answers = body.get("answers", {})
        if not isinstance(answers, dict):
            return JsonResponse(
                {"detail": "answers must be an object"}, status=422
            )
        try:
            normalized = _normalize_answers(answers, bundle)
        except _ParityHTTPError as exc:
            return JsonResponse({"detail": exc.detail}, status=exc.status_code)

        ctx = EvalContext(
            optional_ids=bundle.optional_ids,
            reasons=bundle.reasons,
            fixes=bundle.fixes,
            income_buckets=bundle.income_buckets,
        )
        result = deep_check_scheme(scheme, profile.answers, normalized, ctx, locale)
        profile.deep_check_answers.update(normalized)
        profile.save(update_fields=["deep_check_answers"])
        return Response(result)
