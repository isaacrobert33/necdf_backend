# Create your models here.
from django.contrib.gis.db import models

from netcdf_backend.core.mixins import CreatedAtMixin, UUIDMixin


class NetCDFFile(UUIDMixin, CreatedAtMixin, models.Model):
    file = models.FileField(upload_to="netcdf-files/")

    def __str__(self):
        return self.file.name


class ClimateData(models.Model):
    scenario = models.CharField(
        max_length=10,
        choices=[("ssp245", "SSP-245"), ("ssp585", "SSP-585")],
    )
    variable = models.CharField(
        max_length=10,
        choices=[
            ("pr", "Precipitation"),
            ("tas", "Temperature"),
            ("tasmax", "Max Temperature"),
            ("tasmin", "Min Temperature"),
        ],
    )
    season = models.CharField(
        max_length=10,
        choices=[
            ("DJF", "DJF"),
            ("MAM", "MAM"),
            ("JJA", "JJA"),
            ("SON", "SON"),
            ("ANN", "ANN"),
        ],
    )
    period = models.CharField(max_length=20)  # e.g., '2025-2054'
    latitude = models.FloatField()
    longitude = models.FloatField()
    value = models.FloatField()
    p_value = models.FloatField()
    geom = models.PointField(srid=4326)

    class Meta:
        indexes = [
            models.Index(fields=["scenario", "variable", "season", "period"]),
            # models.Index(fields=["geom"], name="climate_data_geom_idx", using="gist"),  # noqa: E501, ERA001
        ]


class FileCache(models.Model):
    file_type = models.CharField(
        max_length=10,
        choices=[("geotiff", "GeoTIFF"), ("geojson", "GeoJSON")],
    )
    scenario = models.CharField(max_length=10)
    variable = models.CharField(max_length=10)
    season = models.CharField(max_length=10)
    period = models.CharField(max_length=20)
    file = models.FileField(upload_to="caches/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("file_type", "scenario", "variable", "season", "period")
