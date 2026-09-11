import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers

from apps.accounts.models import MOBILE_REGEX, User, normalize_mobile

MOBILE_INVALID_MESSAGE = "Enter a valid 10-digit Indian mobile number."


class RegisterSerializer(serializers.Serializer):
    mobile = serializers.CharField()
    password = serializers.CharField(write_only=True)
    name = serializers.CharField(required=False, allow_blank=True, default="", max_length=200)

    def validate_mobile(self, value):
        mobile = normalize_mobile(value)
        if not re.fullmatch(MOBILE_REGEX, mobile):
            raise serializers.ValidationError(MOBILE_INVALID_MESSAGE)
        return mobile

    def validate(self, attrs):
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(" ".join(exc.messages))
        if User.objects.filter(mobile=attrs["mobile"]).exists():
            raise serializers.ValidationError(
                "An account with this mobile number already exists."
            )
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            mobile=validated_data["mobile"],
            password=validated_data["password"],
            name=validated_data.get("name", ""),
        )
