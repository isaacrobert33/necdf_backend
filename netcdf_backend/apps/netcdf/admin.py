from django.contrib import admin

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
