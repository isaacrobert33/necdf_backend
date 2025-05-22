# Create your models here.
from django.db import models

from netcdf_backend.core.mixins import CreatedAtMixin, UUIDMixin


class NetCDFFile(UUIDMixin, CreatedAtMixin, models.Model):
    file = models.FileField(upload_to="netcdf-files/")

    def __str__(self):
        return self.file.name
