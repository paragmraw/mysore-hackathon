from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import SessionAuthWithoutCSRF
from apps.accounts.models import Profile, normalize_mobile
from apps.accounts.serializers import RegisterSerializer

INVALID_CREDENTIALS_MESSAGE = "Invalid mobile or password."


def _request_data(request) -> dict:
    data = request.data
    return data if isinstance(data, dict) else {}


def _error_detail(exc) -> str:
    detail = getattr(exc, "detail", exc)
    if isinstance(detail, dict):
        parts = []
        for value in detail.values():
            if isinstance(value, (list, tuple)):
                parts.extend(str(item) for item in value)
            else:
                parts.append(str(value))
        return " ".join(parts)
    if isinstance(detail, (list, tuple)):
        return " ".join(str(item) for item in detail)
    return str(detail)


def _user_payload(user) -> dict:
    profile = getattr(user, "profile", None)
    return {
        "mobile": user.mobile,
        "name": user.name,
        "answers": profile.answers if profile is not None else {},
        "deep_check_answers": profile.deep_check_answers if profile is not None else {},
    }


class SessionApiView(APIView):
    authentication_classes = [SessionAuthWithoutCSRF]


class RegisterView(SessionApiView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=_request_data(request))
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            return Response(
                {"detail": _error_detail(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "An account with this mobile number already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response(_user_payload(user), status=status.HTTP_200_OK)


class LoginView(SessionApiView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = _request_data(request)
        mobile = normalize_mobile(str(data.get("mobile") or ""))
        password = str(data.get("password") or "")
        user = authenticate(request, mobile=mobile, password=password)
        if user is None:
            return Response(
                {"detail": INVALID_CREDENTIALS_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response(_user_payload(user), status=status.HTTP_200_OK)


class LogoutView(SessionApiView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({"detail": "ok"}, status=status.HTTP_200_OK)


class MeView(SessionApiView):

    permission_classes = [IsAuthenticated]

    def get_authenticate_header(self, request):
        return "Session"

    def get(self, request):
        return Response(_user_payload(request.user))

    def patch(self, request):
        data = _request_data(request)
        if "name" in data:
            name = data["name"]
            if not isinstance(name, str) or not name.strip():
                return Response(
                    {"detail": "name must be a non-empty string."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            request.user.name = name.strip()
            request.user.save(update_fields=["name"])

        profile = None
        for key in ("answers", "deep_check_answers"):
            if key not in data:
                continue
            value = data[key]
            if not isinstance(value, dict):
                return Response(
                    {"detail": f"{key} must be an object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if profile is None:
                profile, _ = Profile.objects.get_or_create(user=request.user)
            getattr(profile, key).update(value)
        if profile is not None:
            profile.save(update_fields=["answers", "deep_check_answers"])
        return Response(_user_payload(request.user))
