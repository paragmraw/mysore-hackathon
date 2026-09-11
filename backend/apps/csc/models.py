from django.db import models


class CscCenter(models.Model):

    id = models.CharField(max_length=64, primary_key=True)  # slug
    name = models.JSONField()
    address = models.JSONField()
    locality = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    taluk = models.CharField(max_length=100, blank=True, default="")
    pincode = models.CharField(max_length=6)
    lat = models.FloatField()
    lng = models.FloatField()
    phone = models.CharField(max_length=20, null=True, blank=True)
    hours = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.id


class PincodeCentroid(models.Model):

    pincode = models.CharField(max_length=6, primary_key=True)
    lat = models.FloatField()
    lng = models.FloatField()

    class Meta:
        ordering = ["pincode"]

    def __str__(self) -> str:
        return self.pincode
