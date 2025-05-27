import geopandas as gpd
from django.contrib.gis.geos import Point

from netcdf_backend.apps.netcdf.models import ClimateData


def generate_geojson(scenario, variable, season, period, output_path):
    # Query significant points (p_value <= 0.05)
    data = ClimateData.objects.filter(
        scenario=scenario,
        variable=variable,
        season=season,
        period=period,
        p_value__lte=0.05,
    )

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(
        [
            {"value": d.p_value, "geometry": Point(d.longitude, d.latitude)}
            for d in data
        ],
        crs="EPSG:4326",
    )

    # Save to GeoJSON
    gdf.to_file(output_path, driver="GeoJSON")
