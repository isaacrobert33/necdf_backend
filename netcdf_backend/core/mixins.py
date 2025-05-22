import uuid
from datetime import datetime

from django.contrib.gis.db import models as gis_models
from django.db import models


class CreatedAtMixin(models.Model):
    created_at: datetime = models.DateTimeField(auto_now_add=True)

    # https://docs.djangoproject.com/en/3.2/ref/models/options/#abstract
    class Meta:
        abstract = True


class UpdatedAtMixin(models.Model):
    updated_at: datetime = models.DateTimeField(auto_now=True)

    # https://docs.djangoproject.com/en/3.2/ref/models/options/#abstract
    class Meta:
        abstract = True


class UUIDMixin(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # https://docs.djangoproject.com/en/3.2/ref/models/options/#abstract
    class Meta:
        abstract = True


class CoordinatesMixin(models.Model):
    latitude = models.DecimalField(max_digits=9, decimal_places=6, default=0.0)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, default=0.0)
    point = gis_models.PointField(srid=4326, null=True)

    # https://docs.djangoproject.com/en/3.2/ref/models/options/#abstract
    class Meta:
        abstract = True


class CreatedAndUpdatedAtMixin(CreatedAtMixin, UpdatedAtMixin):
    # https://docs.djangoproject.com/en/3.2/ref/models/options/#abstract
    class Meta:
        abstract = True
