# utils.py
import xarray as xr


def extract_netcdf_metadata(file_path: str):
    ds = xr.open_dataset(file_path)

    return {
        "dimensions": {dim: int(size) for dim, size in ds.dims.items()},
        "variables": list(ds.data_vars),
        "coordinates": list(ds.coords),
        "global_attributes": {k: str(v) for k, v in ds.attrs.items()},
        "variable_attributes": {
            var: {k: str(v) for k, v in ds[var].attrs.items()} for var in ds.data_vars
        },
    }
