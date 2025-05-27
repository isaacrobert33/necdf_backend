from celery import shared_task

from netcdf_backend.apps.netcdf.models import FileCache
from netcdf_backend.apps.netcdf.serializers import FilterParameterSerializer
from netcdf_backend.apps.netcdf.services.geojson_generator import generate_geojson
from netcdf_backend.apps.netcdf.services.geotiff import generate_geotiff
from netcdf_backend.apps.netcdf.services.netcdf_preprocess import process_netcdf


@shared_task
def process_and_cache_netcdf(
    file_path,
    filter_serializer: FilterParameterSerializer,
    region_bbox,
):
    data = filter_serializer.validated_data

    scenario = data["scenario"]
    season = data["season"]
    period = data["period"]
    variable = data["variable"]

    # Process NetCDF and store in database
    process_netcdf(file_path, scenario, variable, season, period, region_bbox)

    # Generate and cache GeoTIFF
    geotiff_path = (
        f"cache/change_ensmean_{variable}_{scenario}_{season}_{period}_Tanzania.tiff"
    )
    generate_geotiff(scenario, variable, season, period, region_bbox, geotiff_path)
    FileCache.objects.update_or_create(
        file_type="geotiff",
        scenario=scenario,
        variable=variable,
        season=season,
        period=period,
        defaults={"file_path": geotiff_path},
    )

    # Generate and cache GeoJSON
    geojson_path = (
        f"cache/sig_ensmean_{variable}_{scenario}_{season}_{period}_Tanzania.geojson"
    )
    generate_geojson(scenario, variable, season, period, geojson_path)
    FileCache.objects.update_or_create(
        file_type="geojson",
        scenario=scenario,
        variable=variable,
        season=season,
        period=period,
        defaults={"file_path": geojson_path},
    )
