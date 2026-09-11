from __future__ import annotations

from apps.schemes.serializers import loc_out


def _center_out(center, locale: str, distance_km: float | None) -> dict:
    out = {
        "id": center.id,
        "name": loc_out(center.name, locale),
        "address": loc_out(center.address, locale),
        "locality": center.locality,
        "city": center.city,
        "taluk": center.taluk,
        "pincode": center.pincode,
        "lat": center.lat,
        "lng": center.lng,
    }
    if center.phone is not None:
        out["phone"] = center.phone
    if center.hours is not None:
        out["hours"] = center.hours
    if distance_km is not None:
        out["distance_km"] = round(distance_km, 1)
    return out
