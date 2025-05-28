from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from netcdf_backend.apps.netcdf import models

# Register your models here.


@admin.register(models.NetCDFFile)
class NetCDFFileAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "file",
        "created_at",
    )
    search_fields = (
        "uuid",
        "file",
    )
    readonly_fields = (
        "uuid",
        "created_at",
    )


@admin.register(models.ClimateData)
class ClimateDataAdmin(GISModelAdmin):
    list_display = (
        "variable",
        "scenario",
        "season",
        "period",
    )
    search_fields = (
        "variable",
        "scenario",
        "season",
        "period",
    )
    list_filter = (
        "season",
        "period",
        "variable",
    )


@admin.register(models.FileCache)
class FileCacheAdmin(admin.ModelAdmin):
    list_display = (
        "variable",
        "scenario",
        "season",
        "period",
        "file_type",
    )
    search_fields = (
        "variable",
        "scenario",
        "season",
        "period",
        "file_type",
    )
    list_filter = (
        "season",
        "period",
        "file_type",
    )
