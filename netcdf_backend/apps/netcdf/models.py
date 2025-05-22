# Create your models here.
from django.db import models

from netcdf_backend.core.mixins import CreatedAtMixin
from netcdf_backend.core.mixins import UUIDMixin


class NetCDFile(UUIDMixin, CreatedAtMixin, models.Model):
    file = models.FileField(upload_to="netcdf-files/")

    def __str__(self):
        return self.file.name
