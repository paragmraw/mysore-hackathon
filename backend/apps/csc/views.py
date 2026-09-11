import math

from django.http import JsonResponse
from rest_framework.views import APIView

from apps.csc.serializers import _center_out
from apps.schemes.bundle import get_bundle
from apps.schemes.views import _locale_or_error

MYSURU_CITY_CENTER = {"lat": 12.2958, "lng": 76.6394}

_EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _limit_or_error(request):
    raw = request.query_params.get("limit")
    if raw is None:
        return 5, None
    try:
        limit = int(raw)
    except ValueError:
        return None, JsonResponse({"detail": "limit must be an integer between 1 and 25"}, status=422)
    if not 1 <= limit <= 25:
        return None, JsonResponse({"detail": "limit must be an integer between 1 and 25"}, status=422)
    return limit, None


def _not_karnataka() -> JsonResponse:
    return JsonResponse({"error": "not_karnataka"}, status=422)


class CscView(APIView):
    """GET /csc?pincode=&limit=&locale= — centre lookup with 422 parity."""

    def get(self, request):
        locale, error = _locale_or_error(request)
        if error:
            return error
        limit, error = _limit_or_error(request)
        if error:
            return error

        pincode = request.query_params.get("pincode")
        if pincode is None:
            return JsonResponse(
                {"detail": "pincode: field required"}, status=422
            )
        if not (pincode.isdigit() and len(pincode) == 6):
            return _not_karnataka()
        pin_number = int(pincode)
        if not 560000 <= pin_number <= 599999:
            return _not_karnataka()

        bundle = get_bundle()
        centers = bundle.csc_centers
        centroids = bundle.csc_centroids

        exact = sorted(
            (center for center in centers if center.pincode == pincode),
            key=lambda c: c.id,
        )
        if exact:
            return JsonResponse(
                {
                    "match": "pincode",
                    "centers": [_center_out(center, locale, None) for center in exact],
                }
            )

        origin = centroids.get(pincode)
        if origin is not None:
            ranked = sorted(
                (
                    (
                        _haversine_km(origin["lat"], origin["lng"], center.lat, center.lng),
                        center,
                    )
                    for center in centers
                ),
                key=lambda pair: (pair[0], pair[1].id),
            )[:limit]
            return JsonResponse(
                {
                    "match": "nearby",
                    "centers": [
                        _center_out(center, locale, distance) for distance, center in ranked
                    ],
                }
            )

        if centroids:
            first = next(iter(centroids.values()))
            fallback = {"lat": first["lat"], "lng": first["lng"]}
        else:
            fallback = MYSURU_CITY_CENTER
        ranked = sorted(
            (
                (_haversine_km(fallback["lat"], fallback["lng"], center.lat, center.lng), center)
                for center in centers
            ),
            key=lambda pair: (pair[0], pair[1].id),
        )[:limit]
        return JsonResponse(
            {
                "match": "district_fallback",
                "centers": [
                    _center_out(center, locale, distance) for distance, center in ranked
                ],
                "note": {
                    "en": "Pincode not in our coverage; showing Mysuru district centres",
                    "kn": "Pincode not in our coverage; showing Mysuru district centres",
                },
            }
        )
