from django import forms
from django.contrib import admin

from apps.schemes.models import Fix, IncomeBucket, Question, Reason, Scheme


class OptionalJsonFormMixin:

    optional_json_fields: tuple[str, ...] = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.optional_json_fields:
            if name in self.fields:
                self.fields[name].required = False

    def clean(self):
        cleaned_data = super().clean()
        model = self.Meta.model
        for name in self.optional_json_fields:
            if name in cleaned_data and cleaned_data[name] in (None, [], {}, ()):
                cleaned_data[name] = model._meta.get_field(name).get_default()
        return cleaned_data


class SchemeForm(OptionalJsonFormMixin, forms.ModelForm):
    optional_json_fields = (
        "summ",
        "department",
        "benefit",
        "amount",
        "deadline",
        "eligibility_criteria",
        "application_steps",
        "channels",
        "docs",
        "rules",
        "route",  
        "source_note",
        "confidence_note", 
    )

    class Meta:
        model = Scheme
        fields = "__all__"


class FixForm(OptionalJsonFormMixin, forms.ModelForm):
    optional_json_fields = ("steps",)

    class Meta:
        model = Fix
        fields = "__all__"


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    form = SchemeForm

    list_display = ["id", "code", "benefit_type", "order", "last_verified"]
    list_filter = ["benefit_type", "jurisdiction"]
    search_fields = ["id", "code"]
    ordering = ["order"]

    fieldsets = [
        ("Identity", {"fields": ["id", "code", "order", "benefit_type", "jurisdiction"]}),
        (
            "Copy",
            {
                "fields": [
                    "name",
                    "summ",
                    "department",
                    "benefit",
                    "amount",
                    "deadline",
                    "criteria_note",
                ]
            },
        ),
        (
            "Application",
            {"fields": ["eligibility_criteria", "application_steps", "channels", "docs"]},
        ),
        ("Rules (advanced)", {"fields": ["rules"]}),
        ("Routing", {"fields": ["route"]}),
        ("Provenance", {"fields": ["confidence_note", "last_verified", "source_url", "source_note"]}),
    ]

    def get_readonly_fields(self, request, obj=None):
        return ("id",) if obj is not None else ()


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "type", "optional"]
    list_filter = ["type", "optional"]
    search_fields = ["id"]
    ordering = ["order"]


@admin.register(Reason)
class ReasonAdmin(admin.ModelAdmin):
    list_display = ["code", "message"]
    search_fields = ["code"]


@admin.register(Fix)
class FixAdmin(admin.ModelAdmin):
    form = FixForm

    list_display = ["id", "title"]
    search_fields = ["id"]
    ordering = ["id"]


@admin.register(IncomeBucket)
class IncomeBucketAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "min", "upper"]
    ordering = ["order"]
