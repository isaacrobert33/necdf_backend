from celery import shared_task
from django.conf import settings
from redis import Redis
from redis.exceptions import LockError
from redis.lock import Lock

from netcdf_backend.apps.netcdf.models import FileCache
from netcdf_backend.apps.netcdf.serializers import FilterParameterSerializer
from netcdf_backend.apps.netcdf.services.geojson_generator import generate_geojson
from netcdf_backend.apps.netcdf.services.geotiff import generate_geotiff
from netcdf_backend.apps.netcdf.services.netcdf_preprocess import process_netcdf


@shared_task(bind=True)
def process_and_cache_netcdf(
    self,
    file,
    scenario,
    season,
    period,
    variable,
    region_bbox,
):
    redis_client = Redis.from_url(settings.REDIS_URL)
    lock_key = f"lock:geotiff:{scenario}:{season}:{period}:{variable}"

    # Try to acquire lock with a 5-minute timeout
    with Lock(redis_client, lock_key, timeout=300, blocking_timeout=0):
        try:
            filter_serializer = FilterParameterSerializer(
                data={
                    "scenario": scenario,
                    "season": season,
                    "period": period,
                    "variable": variable,
                },
            )
            # Process NetCDF and store in database
            process_netcdf(
                file,
                filter_serializer=filter_serializer,
                region_bbox=region_bbox,
            )

            # Generate and cache GeoTIFF
            geotiff_path = f"caches/change_ensmean_{variable}_{scenario}_{season}_{period}_Tanzania.tiff"
            print("Generating....")
            geotiff = generate_geotiff(
                filter_serializer=filter_serializer,
                region_bbox=region_bbox,
                output_path=geotiff_path,
            )
            FileCache.objects.update_or_create(
                file_type="geotiff",
                scenario=scenario,
                variable=variable,
                season=season,
                period=period,
                defaults={"file": geotiff},
            )

            # Generate and cache GeoJSON
            geojson_path = f"caches/sig_ensmean_{variable}_{scenario}_{season}_{period}_Tanzania.geojson"
            geojson = generate_geojson(scenario, variable, season, period, geojson_path)
            FileCache.objects.update_or_create(
                file_type="geojson",
                scenario=scenario,
                variable=variable,
                season=season,
                period=period,
                defaults={"file": geojson},
            )
        except LockError:
            # Task is already running
            raise self.retry(countdown=10, max_retries=5)
