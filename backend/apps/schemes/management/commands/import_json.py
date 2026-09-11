import json
from datetime import date
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pydantic import ValidationError

from apps.csc.models import CscCenter as CscCenterModel
from apps.csc.models import PincodeCentroid
from apps.schemes.engine.contract import (
    CscCenter,
    DataBundle,
    DataError,
    FixDef,
    Question,
    ReasonDef,
    SchemeRecord,
    validate_bundle,
)
from apps.schemes.models import Fix, IncomeBucket, Question as QuestionModel, Reason, Scheme

_WARNING_PREFIX = "[namma-mitra] warning: "
_JSON_LIST_KEYS = ("schemes", "items", "questions", "centers")


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise DataError(f"{path}: file not found") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"{path}: invalid JSON ({exc})") from exc


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    data = _read_json(path)
    if isinstance(data, dict):
        for key in _JSON_LIST_KEYS:
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise DataError(f"{path.name}: expected a JSON array")
    return data


def _validate_models(model_cls, raw_items: list, label: str) -> list:
    out = []
    for index, raw in enumerate(raw_items):
        try:
            out.append(model_cls.model_validate(raw))
        except ValidationError as exc:
            raise DataError(f"{label}[{index}]: {exc}") from exc
    return out


def _load_centroids(path: Path) -> dict[str, dict[str, float]]:
    data = _read_json(path)
    entries: dict[str, Any] = {}
    if isinstance(data, dict):
        entries = data.get("pincodes") if isinstance(data.get("pincodes"), dict) else data
    if not isinstance(entries, dict):
        raise DataError(f"{path.name}: expected a pincodes mapping")
    centroids: dict[str, dict[str, float]] = {}
    for pin, value in entries.items():
        if not (isinstance(pin, str) and pin.isdigit() and len(pin) == 6):
            raise DataError(f"{path.name}: bad pincode key {pin!r}")
        if not isinstance(value, dict) or "lat" not in value or "lng" not in value:
            raise DataError(f"{path.name}: centroid {pin} missing lat/lng")
        try:
            centroids[pin] = {"lat": float(value["lat"]), "lng": float(value["lng"])}
        except (TypeError, ValueError) as exc:
            raise DataError(f"{path.name}: centroid {pin} has non-numeric lat/lng") from exc
    return centroids


def _load_income_buckets(path: Path) -> dict[str, dict[str, Any]]:
    data = _read_json(path)
    if not isinstance(data, dict):
        raise DataError(f"{path.name}: expected a bucket mapping")
    for bucket_id, value in data.items():
        if not isinstance(value, dict):
            raise DataError(f"{path.name}: bucket '{bucket_id}' is not an object")
        for key in ("min", "upper"):
            if key in value and value[key] is not None and not isinstance(value[key], (int, float)):
                raise DataError(f"{path.name}: bucket '{bucket_id}' has non-numeric '{key}'")
    return data


def _localized(value) -> dict:
    out = {"en": value.en or ""}
    if value.kn:
        out["kn"] = value.kn
    return out


class Command(BaseCommand):
    help = (
        "Validate the contract JSON files against the Phase 0 contract and "
        "upsert them into the database (schemes + csc apps)."
    )

    def add_arguments(self, parser):
        parser.add_argument("data_dir", nargs="?", default=None,
                            help="Data directory (default: DATA_DIR env, else the repo data/)")

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"] or settings.DATA_DIR)
        if not data_dir.is_dir():
            raise CommandError(f"data directory not found: {data_dir}")

        try:
            bundle, warnings = self._load_and_validate(data_dir)
        except DataError as exc:
            raise CommandError(str(exc)) from exc
        for warning in warnings:
            self.stderr.write(_WARNING_PREFIX + warning)

        with transaction.atomic():
            counts = self._upsert(bundle)
        self.stdout.write(f"Imported from {data_dir}:")
        for label, count in counts:
            self.stdout.write(f"  {label}: {count}")

    def _load_and_validate(self, data_dir: Path) -> tuple[DataBundle, list[str]]:
        """Parse all 7 files through the contract models; raise DataError on violation."""
        questions_raw = _read_json_list(data_dir / "questions.json")
        questions = _validate_models(Question, questions_raw, "questions")
        schemes_raw = _read_json_list(data_dir / "schemes.json")
        schemes = _validate_models(SchemeRecord, schemes_raw, "schemes")
        try:
            reasons = {
                code: ReasonDef.model_validate(spec)
                for code, spec in _read_json(data_dir / "reasons.json").items()
            }
            fixes = {
                fix_id: FixDef.model_validate(spec)
                for fix_id, spec in _read_json(data_dir / "fixes.json").items()
            }
        except ValidationError as exc:
            raise DataError(f"reasons/fixes: {exc}") from exc
        income_buckets = _load_income_buckets(data_dir / "income-buckets.json")
        csc_raw = _read_json_list(data_dir / "csc" / "mysuru.json")
        csc_centers = _validate_models(CscCenter, csc_raw, "csc")
        centroids = _load_centroids(data_dir / "csc" / "pincodes_mysuru.json")

        bundle = DataBundle(
            schemes=schemes,
            schemes_raw=schemes_raw,
            questions=questions,
            reasons=reasons,
            fixes=fixes,
            income_buckets=income_buckets,
            csc_centers=csc_centers,
            csc_centroids=centroids,
        )
        errors, warnings = validate_bundle(bundle, schemes_raw, questions_raw)
        if errors:
            raise DataError("Invalid contract data in %s:\n%s" % (data_dir, "\n".join(errors)))
        return bundle, warnings

    @staticmethod
    def _scheme_defaults(record: SchemeRecord, order: int) -> dict:
        return {
            "code": record.code,
            "order": order,
            "name": _localized(record.name),
            "summ": _localized(record.summ),
            "department": _localized(record.department),
            "benefit_type": record.benefit_type,
            "jurisdiction": record.jurisdiction,
            "benefit": _localized(record.benefit),
            "amount": _localized(record.amount),
            "amount_inr": record.amount_inr,
            "amount_period": record.amount_period,
            "deadline": _localized(record.deadline),
            "eligibility_criteria": [_localized(l) for l in record.eligibility_criteria],
            "application_steps": [_localized(l) for l in record.application_steps],
            "docs": [_localized(l) for l in record.docs],
            "channels": [
                {"type": c.type,
                 **({"label": _localized(c.label)} if c.label else {}),
                 **({"url": c.url} if c.url else {})}
                for c in record.channels
            ],
            "route": record.route.model_dump() if record.route is not None else None,
            "criteria_note": _localized(record.criteria_note) if record.criteria_note else None,
            "rules": record.rules.model_dump(),
            "confidence_note": record.confidence_note,
            "last_verified": date.fromisoformat(record.last_verified),
            "source_url": record.source_url,
            "source_note": _localized(record.source_note),
        }

    @staticmethod
    def _question_defaults(record: Question, order: int) -> dict:
        return {
            "order": order,
            "type": record.type,
            "label": _localized(record.label),
            "options": (
                [{"value": o.value, "label": _localized(o.label)} for o in record.options]
                if record.options is not None else None
            ),
            "cols": record.cols,
            "optional": record.optional,
            # Stored snake_case per the model contract.
            "show_if": record.show_if,
            "stage": record.stage,
            "scheme_id": record.scheme_id,
        }

    def _upsert(self, bundle: DataBundle) -> list[tuple[str, int]]:
        counts: list[tuple[str, int]] = []

        for index, record in enumerate(bundle.schemes):
            Scheme.objects.update_or_create(
                id=record.id,
                defaults=self._scheme_defaults(record, index),
            )
        counts.append(("schemes", len(bundle.schemes)))

        for index, record in enumerate(bundle.questions):
            QuestionModel.objects.update_or_create(
                id=record.id,
                defaults=self._question_defaults(record, index),
            )
        counts.append(("questions", len(bundle.questions)))

        for code, spec in bundle.reasons.items():
            Reason.objects.update_or_create(
                code=code, defaults={"message": _localized(spec.message)}
            )
        counts.append(("reasons", len(bundle.reasons)))

        for fix_id, spec in bundle.fixes.items():
            Fix.objects.update_or_create(
                id=fix_id,
                defaults={
                    "title": _localized(spec.title),
                    "steps": [_localized(s) for s in spec.steps],
                },
            )
        counts.append(("fixes", len(bundle.fixes)))

        for index, (bucket_id, spec) in enumerate(bundle.income_buckets.items()):
            IncomeBucket.objects.update_or_create(
                id=bucket_id,
                defaults={"order": index, "min": spec.get("min"), "upper": spec.get("upper")},
            )
        counts.append(("income_buckets", len(bundle.income_buckets)))

        for record in bundle.csc_centers:
            CscCenterModel.objects.update_or_create(
                id=record.id,
                defaults={
                    "name": _localized(record.name),
                    "address": _localized(record.address),
                    "locality": record.locality,
                    "city": record.city,
                    "taluk": record.taluk,
                    "pincode": record.pincode,
                    "lat": record.lat,
                    "lng": record.lng,
                    "phone": record.phone,
                    "hours": record.hours,
                },
            )
        counts.append(("csc_centers", len(bundle.csc_centers)))

        for pin, value in bundle.csc_centroids.items():
            PincodeCentroid.objects.update_or_create(
                pincode=pin, defaults={"lat": value["lat"], "lng": value["lng"]}
            )
        counts.append(("pincode_centroids", len(bundle.csc_centroids)))

        return counts
