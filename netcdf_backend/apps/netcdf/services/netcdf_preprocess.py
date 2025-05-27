import numpy as np
import xarray as xr
from django.contrib.gis.geos import Point

from netcdf_backend.apps.netcdf.models import ClimateData
from netcdf_backend.apps.netcdf.serializers import FilterParameterSerializer


def process_netcdf(
    file_path,
    filter_serializer: FilterParameterSerializer,
    region_bbox,
):
    filter_serializer.is_valid(raise_exception=True)
    data = filter_serializer.validated_data

    scenario = data["scenario"]
    season = data["season"]
    period = data["period"]
    variable = data["variable"]

    ds = xr.open_dataset(file_path)
    # Subset to region (Tanzania: [29, -11.75, 40.5, -1])
    ds = ds.sel(
        latitude=slice(region_bbox[1], region_bbox[3]),
        longitude=slice(region_bbox[0], region_bbox[2]),
    )

    # Select season and period
    if season != "Annual":
        months = {
            "DJF": [12, 1, 2],
            "MAM": [3, 4, 5],
            "JJA": [6, 7, 8],
            "SON": [9, 10, 11],
        }
        ds = ds.sel(time=ds.time.dt.month.isin(months[season]))

    start_year, end_year = map(int, period.split("-"))
    ds = ds.sel(time=slice(f"{start_year}-01-01", f"{end_year}-12-31"))

    # Aggregate (mean over time)
    data = ds[variable].mean(dim="time").to_numpy()
    p_values = ds.get(
        "p_value",
        np.ones_like(data) * 0.01,
    )  # Mock significance if not in file
    lats = ds.latitude.to_numpy()
    lons = ds.longitude.to_numpy()

    # Save to database
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            if not np.isnan(data[i, j]):
                ClimateData.objects.create(
                    scenario=scenario,
                    variable=variable,
                    season=season,
                    period=period,
                    latitude=lat,
                    longitude=lon,
                    value=data[i, j],
                    p_value=p_values[i, j],
                    geom=Point(lon, lat, srid=4326),
                )
