import logging

import geopandas as gpd
import numpy as np
import xarray as xr
from django.contrib.gis.geos import Point
from rest_framework.exceptions import ValidationError
from scipy.stats import ttest_ind
from shapely.geometry import Point as ShapelyPoint

from netcdf_backend.apps.netcdf.models import ClimateData
from netcdf_backend.apps.netcdf.serializers import FilterParameterSerializer

logger = logging.getLogger(__name__)


def process_netcdf(  # noqa: C901, PLR0912, PLR0915
    file,
    filter_serializer: FilterParameterSerializer,
    region_bbox,
):
    filter_serializer.is_valid(raise_exception=True)
    data = filter_serializer.validated_data

    scenario = data["scenario"]
    season = data["season"]
    period = data["period"]
    variable = data["variable"]

    # Load Tanzania border
    try:
        border = gpd.read_file("netcdf_backend/data/tanzania.geojson")
        border = border.to_crs("EPSG:4326")
        border_geometry = (
            border.geometry.unary_union
        )  # Combine polygons (mainland + islands)
    except Exception as e:
        logger.exception(f"Failed to load border file: {e!s}")
        msg = "Invalid Tanzania border file"
        raise ValidationError(msg)  # noqa: B904

    # Load and subset NetCDF
    try:
        ds = xr.open_dataset(file)
        # Ensure dataset covers expected range
        if "lat" not in ds.coords or "lon" not in ds.coords:
            msg = "Expected 'latitude' and 'longitude' coordinates not found"
            raise ValidationError(  # noqa: TRY301
                msg,
            )

        # Subset to Tanzania with nearest neighbor to avoid empty slices
        ds = ds.sel(
            lat=slice(region_bbox[1], region_bbox[3]),
            lon=slice(region_bbox[0], region_bbox[2]),
        )
    except Exception as e:  # noqa: BLE001
        msg = f"Failed to load or subset NetCDF file: {e!s}"
        raise ValidationError(msg)  # noqa: B904

    # Load and subset of historical NetCDF
    try:
        hist_ds = xr.open_dataset(
            f"netcdf_backend/data/annual/{variable}_day_Ensmean_historical_r1i1p1f1_gr_merged.nc",
        )

        # Subset to Tanzania with nearest neighbor to avoid empty slices
        hist_ds = hist_ds.sel(
            lat=slice(region_bbox[1], region_bbox[3]),
            lon=slice(region_bbox[0], region_bbox[2]),
        )
    except Exception as e:  # noqa: BLE001
        msg = f"Failed to load or subset NetCDF file: {e!s}"
        raise ValidationError(msg)  # noqa: B904

    # Get coordinates
    lats = ds.lat.to_numpy()
    lons = ds.lon.to_numpy()

    # Handle 2D coordinates (curvilinear grids)
    if lats.ndim == 2:
        logger.warning("2D latitude/longitude detected, flattening to 1D")
        lats = lats[:, 0] if lats.shape[1] > 1 else lats[0, :]
        lons = lons[0, :] if lons.shape[0] > 1 else lons[:, 0]

    # Check for empty or insufficient data
    if len(lats) == 0 or len(lons) == 0:
        logger.warning(
            f"No data in bounding box {region_bbox}. Expanding search.",
        )
        ds = xr.open_dataset(file)
        lats = ds.lat.to_numpy()
        lons = ds.lon.to_numpy()

        # Filter to points near Tanzania
        lats = lats[(lats >= region_bbox[1] - 1) & (lats <= region_bbox[3] + 1)]
        lons = lons[(lons >= region_bbox[0] - 1) & (lons <= region_bbox[2] + 1)]

        if len(lats) == 0 or len(lons) == 0:
            msg = "No data points found in or near Tanzania"
            raise ValidationError(msg)

        ds = ds.sel(lat=lats, lon=lons, method="nearest")
        lats = ds.lat.to_numpy()
        lons = ds.lon.to_numpy()

    # Select season and period
    # try:  # noqa: ERA001
    # if season != 'ANN':
    #     months = {'DJF': [12, 1, 2], 'MAM': [3, 4, 5], 'JJA': [6, 7, 8], 'SON': [9, 10, 11]}  # noqa: ERA001
    #     ds = ds.sel(time=ds.time.dt.month.isin(months[season]))  # noqa: ERA001

    start_year, end_year = map(int, period.split("-"))
    ds = ds.sel(time=slice(f"{start_year}-01-01", f"{end_year}-12-31"))

    historical = hist_ds[variable].sel(time=slice("1980", "2010"))
    historical = historical.groupby("time.year").mean("time")
    future = ds[variable].groupby("time.year").mean("time")

    _, p_values = ttest_ind(historical, future, axis=0, nan_policy="omit")

    # Aggregate over time
    if "time" not in ds.dims or len(ds.time) == 0:
        logger.warning(
            "No time dimension or empty time slice, using first available data",
        )
        data = ds[variable].to_numpy()
        # p_values = ds.get("p_value", np.ones_like(data) * 0.01)
    else:
        data = ds[variable].mean(dim="time").to_numpy()
        # p_values = ds.get("p_value", np.ones_like(data) * 0.01)

    p_values = np.asarray(p_values)
    logger.info(p_values)

    # except Exception as e:
    #     logger.error(f"Error processing season/period: {e!s}")

    # Interpolate if too coarse (e.g., fewer than 5 points in any dimension)
    # if len(lats) < 5 or len(lons) < 5:
    #     logger.info(
    #         f"Coarse grid detected (lats: {len(lats)}, lons: {len(lons)}), interpolating",
    #     )
    #     target_lats = np.linspace(
    #         max(-39.9, region_bbox[1]),
    #         min(39.9, region_bbox[3]),
    #         50,
    #     )
    #     target_lons = np.linspace(
    #         max(-24.9, region_bbox[0]),
    #         min(54.9, region_bbox[2]),
    #         50,
    #     )
    #     ds = ds.interp(lat=target_lats, lon=target_lons, method="linear")
    #     data = ds[variable].mean(dim="time").to_numpy()
    #     # p_values = ds.get("p_value", np.ones_like(data) * 0.01)
    #     lats = target_lats
    #     lons = target_lons

    # Ensure 2D data
    if data.ndim == 0:
        logger.warning("Scalar data detected, converting to 2D")
        data = np.array([[data.item()]])
        p_values = np.array([[p_values.item()]])
    elif data.ndim == 1:
        logger.warning(
            f"1D data detected (shape: {data.shape}), reshaping to 2D",
        )
        data = data.reshape(-1, 1) if len(lats) == 1 else data.reshape(1, -1)
        p_values = (
            p_values.reshape(-1, 1) if len(lats) == 1 else p_values.reshape(1, -1)
        )

    # Validate shape
    if data.shape != (len(lats), len(lons)):
        logger.error(
            f"Shape mismatch: data.shape={data.shape}, expected=({len(lats)}, {len(lons)})",  # noqa: E501, G004
        )
        msg = f"Data shape {data.shape} does not match coordinates ({len(lats)}, {len(lons)})"
        raise ValidationError(
            msg,
        )

    # Log shapes for debugging
    logger.info(
        f"Processed data: shape={data.shape}, lats={len(lats)}, lons={len(lons)}",  # noqa: G004
    )

    # Clip to Tanzania border
    records = []
    for i in range(len(lats)):
        for j in range(len(lons)):
            if not np.isnan(data[i, j]):
                point = Point(float(lons[j]), float(lats[i]))
                if border_geometry.contains(
                    ShapelyPoint(float(lons[j]), float(lats[i])),
                ):  # Check if point is within border
                    records.append(
                        ClimateData(
                            scenario=scenario,
                            variable=variable,
                            season=season,
                            period=period,
                            latitude=float(lats[i]),
                            longitude=float(lons[j]),
                            value=float(data[i, j]),
                            p_value=float(p_values[i, j]),
                            geom=point,
                        ),
                    )

    # Store in database

    existing_data_count = ClimateData.objects.filter(
        scenario=scenario,
        variable=variable,
        season=season,
        period=period,
    ).count()

    print(existing_data_count, len(lats) * len(lons))

    if existing_data_count == 0:
        ClimateData.objects.bulk_create(objs=records)
