import numpy as np
import rasterio
from rasterio.transform import from_bounds

from netcdf_backend.apps.netcdf.models import ClimateData
from netcdf_backend.apps.netcdf.serializers import FilterParameterSerializer


def generate_geotiff(
    scenario,
    filter_serializer: FilterParameterSerializer,
    region_bbox,
    output_path,
):
    filter_serializer.is_valid(raise_exception=True)
    data = filter_serializer.validated_data

    scenario = data["scenario"]
    season = data["season"]
    period = data["period"]
    variable = data["variable"]

    # Query database
    data = ClimateData.objects.filter(
        scenario=scenario,
        variable=variable,
        season=season,
        period=period,
    ).order_by("latitude", "longitude")

    # Create grid
    lats = sorted({d.latitude for d in data})
    lons = sorted({d.longitude for d in data})
    values = np.array([d.value for d in data]).reshape(len(lats), len(lons))

    # Flip latitude to match GeoTIFF (top-left origin)
    values = np.flipud(values)
    lats = lats[::-1]

    # Define GeoTIFF metadata
    transform = from_bounds(*region_bbox, len(lons), len(lats))
    meta = {
        "driver": "GTiff",
        "height": len(lats),
        "width": len(lons),
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
    }

    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(values, 1)
