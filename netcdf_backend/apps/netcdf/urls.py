from django.urls import path

from netcdf_backend.apps.netcdf.views import (
    GeoJSONView,
    GeoTIFFView,
    NCDataPlot,
    NetCDFMetadata,
    NetCDFUploadView,
)

app_name = "netcdf"

urlpatterns = [
    path("uploads/", NetCDFUploadView.as_view(), name="netcdf-upload"),
    path("metadata/<uuid:uuid>/", NetCDFMetadata.as_view(), name="netcdf-metadata"),
    path("plots/<uuid:uuid>/", NCDataPlot.as_view(), name="netcdf-plot"),
    path("geotiff/", GeoTIFFView.as_view(), name="geotiff"),
    path("geojson/", GeoJSONView.as_view(), name="geojson"),
]
