from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from pydantic import ValidationError as PydanticValidationError

from apps.schemes.engine import contract


_EMPTY_RULES = {"eligibility": [], "exclusions": [], "fixes": [], "deep_check": []}


def _empty_localized() -> dict:
    return {"en": ""}


def _empty_rules() -> dict:
    return {"eligibility": [], "exclusions": [], "fixes": [], "deep_check": []}


def _localized(value, field_label: str) -> dict:
    try:
        contract.Localized.model_validate(value)
    except PydanticValidationError as exc:
        raise DjangoValidationError({field_label: str(exc)}) from exc
    return value


class Scheme(models.Model):

    id = models.CharField(max_length=64, primary_key=True)  # slug
    code = models.CharField(max_length=64, unique=True)
    # Position in the source JSON array; keeps the file's order in the DB.
    order = models.PositiveIntegerField(unique=True)

    name = models.JSONField()
    summ = models.JSONField(default=_empty_localized)
    department = models.JSONField(default=_empty_localized)

    benefit_type = models.CharField(
        max_length=32,
        blank=True,
        default="",
        choices=[
            ("cash_transfer", "cash_transfer"),
            ("subsidy", "subsidy"),
            ("in_kind", "in_kind"),
            ("service", "service"),
        ],
    )
    jurisdiction = models.CharField(
        max_length=32,
        blank=True,
        default="",
        choices=[
            ("karnataka", "karnataka"),
            ("karnataka_central", "karnataka_central"),
        ],
    )

    benefit = models.JSONField(default=_empty_localized)
    amount = models.JSONField(default=_empty_localized)
    amount_inr = models.FloatField(null=True, blank=True)
    amount_period = models.CharField(
        max_length=16,
        blank=True,
        default="",
        choices=[("month", "month"), ("one-time", "one-time"), ("year", "year")],
    )
    deadline = models.JSONField(default=_empty_localized)

    eligibility_criteria = models.JSONField(default=list)
    application_steps = models.JSONField(default=list)
    docs = models.JSONField(default=list)
    channels = models.JSONField(default=list)
    route = models.JSONField(null=True, blank=True)
    criteria_note = models.JSONField(null=True, blank=True)
    rules = models.JSONField(default=_empty_rules)
    confidence_note = models.CharField(max_length=64, default="screening_only")

    last_verified = models.DateField()
    source_url = models.CharField(max_length=500, blank=True, default="")
    source_note = models.JSONField(default=_empty_localized)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.id

    def clean(self) -> None:
        errors: dict[str, str] = {}

        try:
            rules = contract.Rules.model_validate(self.rules or dict(_EMPTY_RULES))
        except PydanticValidationError as exc:
            rules, errors["rules"] = None, str(exc)
        if rules is not None:
            rule_errors = [
                f"rule {rule_id}: {error}"
                for rule_id, check in (
                    [(r.id, r.check) for r in rules.eligibility]
                    + [(r.id, r.check) for r in rules.exclusions]
                    + [(r.id, r.check) for r in rules.fixes]
                    + [(r.id, r.check) for r in rules.deep_check]
                )
                for error in contract.check_rule(check, None)
            ]
            if rule_errors:
                errors["rules"] = "; ".join(rule_errors)

        _localized(self.name, "name")

        if self.route is not None:
            try:
                route = contract.Route.model_validate(self.route)
            except PydanticValidationError as exc:
                errors["route"] = str(exc)
            else:
                if route.group not in contract._ROUTE_GROUPS:
                    errors["route"] = (
                        f"route group '{route.group}' not in {sorted(contract._ROUTE_GROUPS)}"
                    )
                elif route.value not in contract._ROUTE_VALUES[route.group]:
                    errors["route"] = (
                        f"route value '{route.value}' is not a known routed value "
                        f"for group '{route.group}'"
                    )

        valid_benefit_types = {value for value, _ in self._meta.get_field("benefit_type").choices}
        if self.benefit_type and self.benefit_type not in valid_benefit_types:
            errors["benefit_type"] = (
                f"benefit_type '{self.benefit_type}' not in {sorted(valid_benefit_types)}"
            )

        valid_jurisdictions = {
            value for value, _ in self._meta.get_field("jurisdiction").choices
        }
        if self.jurisdiction and self.jurisdiction not in valid_jurisdictions:
            errors["jurisdiction"] = (
                f"jurisdiction '{self.jurisdiction}' not in {sorted(valid_jurisdictions)}"
            )

        if errors:
            raise DjangoValidationError(errors)


class Question(models.Model):

    id = models.CharField(max_length=64, primary_key=True)  # slug
    order = models.PositiveIntegerField()
    type = models.CharField(
        max_length=32,
        choices=[
            ("single_select", "single_select"),
            ("number", "number"),
            ("pincode", "pincode"),
        ],
    )
    label = models.JSONField()
    options = models.JSONField(null=True, blank=True)
    cols = models.PositiveIntegerField(null=True, blank=True)
    optional = models.BooleanField(default=False)
    show_if = models.JSONField(null=True, blank=True)
    stage = models.JSONField(default=list)
    scheme_id = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.id


class Reason(models.Model):
    code = models.CharField(max_length=64, primary_key=True)
    message = models.JSONField()

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Fix(models.Model):
    id = models.CharField(max_length=64, primary_key=True)  
    title = models.JSONField()
    steps = models.JSONField(default=list)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.id


class IncomeBucket(models.Model):

    id = models.CharField(max_length=64, primary_key=True) 
    order = models.PositiveIntegerField()
    min = models.FloatField(null=True, blank=True)
    upper = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.id
