from django.contrib import admin

from apps.csc.models import CscCenter, PincodeCentroid


@admin.register(CscCenter)
class CscCenterAdmin(admin.ModelAdmin):
    list_display = ["id", "pincode", "city", "taluk", "phone"]
    list_filter = ["city"]
    search_fields = ["pincode", "city", "taluk"]
    ordering = ["id"]


@admin.register(PincodeCentroid)
class PincodeCentroidAdmin(admin.ModelAdmin):
    list_display = ["pincode", "lat", "lng"]
    search_fields = ["pincode"]
    ordering = ["pincode"]
