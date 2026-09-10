from rest_framework import serializers

from .models import Scheme, UserSchemeResult


class SchemeSerializer(serializers.Serializer):
    class Meta:
        modle=Scheme
        fields=[
            "id",
            "slug",
            "code",
            "name_en",
            "summary_en",
            "department_en",
            "benifit_en",
            "amount_en",
            "eligibility_criteria",
            "documents_requied",
            "application_steps",
            "source_url",
            "is_active"
        ]

class UserSchemeResultSerializer(serializers.Serialzier):
    schema = SchemaSerializer(read_only=True)

    class Meta:
        modle=UserSchemeResult
        fields=[
            "id",
            "schema",
            "status",
            "reason",
            "blocker",
            "next_action",
            "priority_score",
            "checked_at"
        ]