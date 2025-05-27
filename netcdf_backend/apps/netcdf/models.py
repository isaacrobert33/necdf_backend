# Create your models here.
from django.db import models

from netcdf_backend.core.mixins import CreatedAtMixin
from netcdf_backend.core.mixins import UUIDMixin


class NetCDFFile(UUIDMixin, CreatedAtMixin, models.Model):
    file = models.FileField(upload_to="netcdf-files/")

    def __str__(self):
        return self.file.name


class ClimateData(models.Model):
    scenario = models.CharField(max_length=50)
    variable = models.CharField(max_length=50)
    season = models.CharField(max_length=10)
    period = models.CharField(max_length=20)
    geom = models.PointField(srid=4326)  # EPSG:4326 for lat/lon
    value = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["scenario", "variable", "season", "period"])]
        spatial_index = True

    def __str__(self):
        return f"Scenario: {self.scenario} Var: {self.variable} season: {self.season}"


class SignificanceData(models.Model):
    scenario = models.CharField(max_length=50)
    variable = models.CharField(max_length=50)
    season = models.CharField(max_length=10)
    period = models.CharField(max_length=20)
    geom = models.PointField(srid=4326)
    value = models.FloatField()  # p-value

    class Meta:
        indexes = [models.Index(fields=["scenario", "variable", "season", "period"])]
        spatial_index = True

    def __str__(self):
        return f"Scenario: {self.scenario} Var: {self.variable} season: {self.season}"
