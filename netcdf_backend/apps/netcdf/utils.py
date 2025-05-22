import base64
import io
import json
import os
import traceback

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import xarray as xr
from cftime import DatetimeNoLeap

from netcdf_backend.apps.netcdf.serializers import NetCDFFile, PlotRequestSerializer


def find_coord_var_for_dim(ds, dim):
    for var in ds.variables:
        if ds[var].dims == (dim,):  # exactly one dimension
            return var
    return None


def convert_cftime(obj):
    if isinstance(obj, DatetimeNoLeap):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def extract_netcdf_metadata(file_path: str):
    ds = xr.open_dataset(file_path)

    # Extract variables
    variables = []
    for var_name in ds.data_vars:
        var = ds[var_name]
        variables.append(
            {
                "name": var_name,
                "longName": var.attrs.get("long_name", ""),
                "units": var.attrs.get("units", ""),
                "dimensions": list(var.dims),
                "shape": list(var.shape),
            }
        )

    # Extract dimensions
    dimensions = []

    for dim in ds.dims:
        dim_values = ds.coords[dim].values if dim in ds.coords else None
        var_key = find_coord_var_for_dim(ds, dim)

        if dim_values is None:
            var_values = ds[var_key].values if var_key else None
            if (
                var_values is not None
                and var_values.size > 0
                and not np.all(np.isnan(var_values))
                and var_key in ds.variables
            ):
                ds = ds.set_coords(var_key)

        dim_values = ds.coords[var_key].values if var_key in ds.coords else None
        values = None

        if dim_values is not None and len(dim_values) <= 1000:
            # Handle datetime values: convert to ISO format
            if np.issubdtype(dim_values.dtype, np.datetime64):
                # Convert datetime64[ns] → pandas datetime → ISO
                values = (
                    pd.to_datetime(dim_values).strftime("%Y-%m-%dT%H:%M:%S").tolist()
                )
            else:
                values = dim_values.tolist()

        dimensions.append(
            {
                "name": dim,
                "length": int(ds.dims[dim]),
                "values": values,
            }
        )

    # Identify lat/lon dims
    lat_dim = "lat" if "lat" in ds.dims else "latitude"
    lon_dim = "lon" if "lon" in ds.dims else "longitude"

    # Add lat/lon range info
    lat_range, lon_range = [], []

    if lat_dim not in ds:
        lat_dim = find_coord_var_for_dim(ds, lat_dim)

    if lon_dim not in ds:
        lon_dim = find_coord_var_for_dim(ds, lon_dim)

    if lat_dim in ds:
        lat_values = ds[lat_dim].values
        lat_range = [float(np.min(lat_values)), float(np.max(lat_values))]
    if lon_dim in ds:
        lon_values = ds[lon_dim].values
        lon_range = [float(np.min(lon_values)), float(np.max(lon_values))]

    # Extract global metadata
    metadata_keys = [
        "title",
        "institution",
        "source",
        "history",
        "references",
        "comment",
        "conventions",
    ]
    metadata = {key: str(ds.attrs.get(key, "")) for key in metadata_keys}

    return json.loads(
        json.dumps(
            {
                "filename": os.path.basename(file_path),
                "variables": variables,
                "dimensions": dimensions,
                "metadata": metadata,
                "lat_range": lat_range,
                "lon_range": lon_range,
            },
            default=convert_cftime,
        )
    )


def plot_temperature_map(da: xr.DataArray, var: str, lat_dim: str, lon_dim: str):

    # Set up the plot
    fig, ax = plt.subplots(
        figsize=(10, 6), subplot_kw={"projection": ccrs.PlateCarree()}
    )
    ax.set_title(f"{var.capitalize()} Map")

    if "time" in da.dims:
        da = da.isel(time=0)

    if da.ndim != 2 or da.shape[0] < 2 or da.shape[1] < 2:
        plt.close(fig)
        return None

    # Filled contour
    contourf = ax.contourf(
        da[lon_dim],
        da[lat_dim],
        da.values,
        levels=20,
        cmap="Spectral_r",
        transform=ccrs.PlateCarree(),
    )

    # Contour lines
    contours = ax.contour(
        da[lon_dim],
        da[lat_dim],
        da.values,
        colors="black",
        linewidths=0.5,
        transform=ccrs.PlateCarree(),
    )
    ax.clabel(contours, inline=True, fontsize=8)

    # Add map features
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS)
    ax.add_feature(cfeature.RIVERS, linestyle=":")
    ax.add_feature(cfeature.LAND, edgecolor="black")

    # Colorbar
    cbar = plt.colorbar(contourf, ax=ax, orientation="vertical", shrink=0.7)
    cbar.set_label("Temperature (°C)")

    # Return image as base64
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    spatial_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{spatial_base64}"


def get_spatial_plot(da: xr.DataArray, var: str):
    # Average over time (or other dimensions) if present
    fig, ax = plt.subplots(figsize=(8, 5))

    if "time" in da.dims:
        da = da.groupby("time.month").mean(dim="time")

    # Collapse all other dims except lat/lon
    for d in da.dims:
        if d not in ["lat", "latitude", "lon", "longitude", "month"]:
            da = da.isel({d: 0})

    data2D = da.mean(dim="month")  # Average over months

    data2D.plot(ax=ax)
    ax.set_title(f"Mean {var} Spatial Plot")

    # Return image as base64
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    spatial_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{spatial_base64}"


def get_timeseries(
    ds: xr.Dataset,
    da: xr.DataArray,
    lat: int,
    lon: int,
    var: str,
    lat_dim: str,
    lon_dim: str,
):
    # elif plot_type == "timeseries":
    # Find nearest lat/lon
    fig, ax = plt.subplots(figsize=(8, 5))
    da = da.sel({lat_dim: lat, lon_dim: lon}, method="nearest")

    if "time" not in da.coords:
        return None

    # Convert time to datetime if needed
    if np.issubdtype(da["time"].dtype, np.datetime64):
        times = pd.to_datetime(da["time"].values)
    else:
        times = pd.to_datetime([t.isoformat() for t in da["time"].values])

    print(times)
    ax.plot(times, da.values)

    if lat and lon:
        ax.set_title(f"Time Series of {var} at ({lat}, {lon})")
    else:
        ax.set_title("Time Series")

    ax.set_xlabel("Time")
    ax.set_ylabel(var)

    # Return image as base64
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    timeseries_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{timeseries_base64}"


def generate_plotly_geospatial_map(
    da: xr.DataArray, var_name: str, lat_dim: str, lon_dim: str
):
    """
    Generate a spatial map from a 2D DataArray over latitude and longitude using Plotly.

    Parameters:
        da (xr.DataArray): A 2D DataArray with dimensions (lat, lon) or (latitude, longitude)
        var_name (str): The name of the variable for labeling

    Returns:
        dict: Plotly figure dictionary (JSON-serializable)
    """
    # Ensure coordinate arrays
    lat_vals = da[lat_dim].values
    lon_vals = da[lon_dim].values
    z_vals = da.values

    if "time" in da.dims:
        da = da.isel(time=0)

    # Make sure data is 2D
    if da.ndim != 2:
        return None

    # Create meshgrid for lat/lon positions
    lon_mesh, lat_mesh = np.meshgrid(lon_vals, lat_vals)

    # Flatten all arrays for scatter plotting
    flat_lat = lat_mesh.flatten()
    flat_lon = lon_mesh.flatten()
    flat_vals = z_vals.flatten()

    # Create Plotly Mapbox scatter plot
    fig = go.Figure(
        go.Densitymapbox(
            lat=flat_lat,
            lon=flat_lon,
            z=flat_vals,
            radius=8,
            colorscale="Viridis",
            colorbar=dict(title=var_name),
            zmin=np.nanmin(flat_vals),
            zmax=np.nanmax(flat_vals),
        )
    )

    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=3,
        mapbox_center={
            "lat": float(np.nanmean(flat_lat)),
            "lon": float(np.nanmean(flat_lon)),
        },
        margin={"r": 0, "t": 30, "l": 0, "b": 0},
        title=f"Spatial Map of {var_name}",
    )

    return fig.to_dict()


def get_coordinates_dim(dims: tuple, coord_type: str):
    """
    Get coordinates in its different forms in dims
        dims: tuple[str]
        coord_type: 'lat' | 'lon
    """
    forms = {
        "lat": "latitude",
        "lon": "longitude",
        "longitude": "lon",
        "latitude": "lat",
    }
    if coord_type in dims:
        return coord_type

    return forms.get(coord_type) if forms.get(coord_type) in dims else None


def create_plot_from_filter(serializer: PlotRequestSerializer) -> tuple[dict, str]:
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        nc_file = NetCDFFile.objects.get(uuid=data["uuid"])
        ds = xr.open_dataset(nc_file.file.path)
    except NetCDFFile.DoesNotExist:
        return {"error": "File not found."}, "error"

    var = data["variable"]
    filters = data.get("filters", {})
    lat = data.get("lat")
    lon = data.get("lon")

    if var not in ds:
        return {"error": f"Variable '{var}' not found in dataset."}, "error"

    da: xr.DataArray = ds[var]

    lat_dim = get_coordinates_dim(da.dims, "lat")
    lon_dim = get_coordinates_dim(da.dims, "lon")

    if lat_dim not in da.coords or lon_dim not in da.coords:
        lat_var_key = find_coord_var_for_dim(ds, lat_dim)
        lon_var_key = find_coord_var_for_dim(ds, lon_dim)
        da = da.assign_coords({lat_dim: ds[lat_var_key], lon_dim: ds[lon_var_key]})

    # Apply filters to all available dimensions
    for dim, vals in filters.items():
        if dim in da.dims:
            if isinstance(vals, list) and len(vals) == 2:
                # Assume it's a range
                da = da.sel({dim: slice(vals[0], vals[1])})
            else:
                da = da.sel({dim: vals})

    # Sort
    if lat_dim and lon_dim:
        da = da.sortby([lat_dim, lon_dim])

    min_lat = data.get("min_lat")
    max_lat = data.get("max_lat")
    min_lon = data.get("min_lon")
    max_lon = data.get("max_lon")

    # Apply bounding box if present

    if min_lat is not None and max_lat is not None:
        da = da.sel({lat_dim: slice(min_lat, max_lat)})
    if min_lon is not None and max_lon is not None:
        da = da.sel({lon_dim: slice(min_lon, max_lon)})

    if lat and lon and lat_dim in da.coords:
        da = da.sel({lat_dim: [lat], lon_dim: [lon]}, method="nearest")

    try:
        spatial_plot = plot_temperature_map(
            da, var=var, lat_dim=lat_dim, lon_dim=lon_dim
        )
    except Exception:
        print(traceback.format_exc())
        spatial_plot = None
    try:
        plotly_map_data = generate_plotly_geospatial_map(
            da, var_name=var, lat_dim=lat_dim, lon_dim=lon_dim
        )
    except Exception:
        print(traceback.format_exc())
        plotly_map_data = None

    try:
        timeseries = get_timeseries(
            ds, da, lat=lat, lon=lon, var=var, lat_dim=lat_dim, lon_dim=lon_dim
        )
    except Exception:
        print(traceback.format_exc())
        timeseries = None

    # except ValueError:
    #     return {"error": "Invalid data format, unable to produce plots"}, "error"

    return {
        "spatial_image": spatial_plot,
        "timeseries_image": timeseries,
        "plotly": plotly_map_data,
    }, "success"
