from pathlib import Path

import numpy as np
import rasterio
from django.core.files import File
from geopandas import read_file
from rasterio.features import geometry_mask
from rasterio.transform import from_bounds

from netcdf_backend.apps.netcdf.models import ClimateData
from netcdf_backend.apps.netcdf.serializers import FilterParameterSerializer


def generate_geotiff(
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

    # Load border
    try:
        border = read_file("netcdf_backend/data/tanzania.geojson").to_crs("EPSG:4326")
    except Exception as e:
        print(f"Failed to load border file: {e!s}")
        raise ValueError("Invalid Tanzania border file")

    # Create grid
    lats = sorted({d.latitude for d in data})
    lons = sorted({d.longitude for d in data})

    lat_idx = {lat: i for i, lat in enumerate(lats)}
    lon_idx = {lon: i for i, lon in enumerate(lons)}
    grid = np.full((len(lats), len(lons)), np.nan, dtype=np.float32)

    for d in data:
        i = lat_idx[d.latitude]
        j = lon_idx[d.longitude]
        grid[i, j] = d.value

    # Flip latitude to match GeoTIFF (top-left origin)
    values = np.flipud(grid)
    lats = lats[::-1]

    # Define GeoTIFF metadata
    transform = from_bounds(*region_bbox, len(lons), len(lats))

    # Mask areas outside Tanzania
    mask = geometry_mask(
        border.geometry,
        out_shape=grid.shape,
        transform=transform,
        invert=True,
    )

    values[~mask] = np.nan

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

    file = Path.open(output_path, "rb")
    return File(file, name=file.name)
