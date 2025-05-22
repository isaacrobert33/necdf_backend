from django.urls import path

from netcdf_backend.apps.netcdf.views import NetCDFMetadata, NetCDFUploadView

app_name = "netcdf"

urlpatterns = [
    path("uploads/", NetCDFUploadView.as_view(), name="netcdf-upload"),
    path("metadata/", NetCDFMetadata.as_view(), name="netcdf-metadata"),
]
