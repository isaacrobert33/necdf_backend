from pathlib import Path
from typing import Any

from django.core.files import File
from geopandas import GeoDataFrame, read_file
from shapely.geometry import Point as ShapelyPoint  # Import shapely Point explicitly

from netcdf_backend.apps.netcdf.models import ClimateData


def generate_geojson(
    scenario: Any,
    variable: Any,
    season: Any,
    period: Any,
    output_path: str,
) -> File:
    # Query significant points (p_value <= 0.05)
    data = ClimateData.objects.filter(
        scenario=scenario,
        variable=variable,
        season=season,
        period=period,
        p_value__lte=0.05,
    )

    # Load border
    try:
        border = read_file("netcdf_backend/data/tanzania.geojson").to_crs("EPSG:4326")
    except Exception as e:
        print(f"Failed to load border file: {e!s}")
        raise ValueError("Invalid Tanzania border file")

    # Create GeoDataFrame
    records = [
        {
            "value": d.p_value,
            "longitude": d.longitude,
            "latitude": d.latitude,
            "geometry": ShapelyPoint(d.longitude, d.latitude),
        }
        for d in data
        if border.geometry.unary_union.contains(ShapelyPoint(d.longitude, d.latitude))
    ]

    gdf = GeoDataFrame(records, crs="EPSG:4326")

    # Save to GeoJSON
    gdf.to_file(output_path, driver="GeoJSON")

    file_path = Path(output_path)
    file = file_path.open("rb")
    return File(file, name=file_path.name)
