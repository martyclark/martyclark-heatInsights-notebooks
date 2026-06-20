"""
utils/heat.py — shared functions for the heat threshold analysis pipeline.

Pipeline order:
  01_data_acquisition  →  calls extract_city_tmax()
  02_compute_baselines →  calls load_city(), percentile_baseline()
  03_threshold_analysis → calls load_city(), load_baseline(), plot helpers
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Union

import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr


# ---------------------------------------------------------------------------
# City registry
# ---------------------------------------------------------------------------

CITIES: dict[str, dict] = {
    'salvador': {
        'bbox':         {'west': -38.8, 'east': -38.2, 'south': -13.2, 'north': -12.7},
        'ibge_code':    2927408,
        'label':        'Salvador, Brazil',
        'gee_collection': 'projects/sat-io/open-datasets/global-daily-air-temp/latin_america',
    },
    'teresina': {
        'bbox':         {'west': -43.2, 'east': -42.5, 'south': -5.4, 'north': -4.8},
        'ibge_code':    2211001,
        'label':        'Teresina, Brazil',
        'gee_collection': 'projects/sat-io/open-datasets/global-daily-air-temp/latin_america',
    },
    'caceres': {
        # Cáceres, Mato Grosso — verify bbox against GEE footprint on first run
        'bbox':         {'west': -58.1, 'east': -57.3, 'south': -16.5, 'north': -15.7},
        'ibge_code':    5102504,
        'label':        'Cáceres, Brazil',
        'gee_collection': 'projects/sat-io/open-datasets/global-daily-air-temp/latin_america',
    },
}

_GEOBR_CACHE_TPL = '{data_dir}/geobr_{city}_neighbourhoods_2010.gpkg'


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_city(name: str, data_dir: str = 'data') -> xr.DataArray:
    """
    Load cached daily Tmax DataArray (time, lat, lon) for a named city.

    Raises FileNotFoundError if 01_data_acquisition has not been run.
    """
    path = Path(data_dir) / f'{name}_tmax.nc'
    if not path.exists():
        raise FileNotFoundError(
            f'Cache not found: {path}\nRun 01_data_acquisition.ipynb first.'
        )
    da = xr.open_dataset(path)['tmax'].load()
    print(f'{name}: shape {dict(zip(da.dims, da.shape))}  '
          f'{str(da.time.values[0])[:10]} to {str(da.time.values[-1])[:10]}')
    return da


def load_city_tmin(name: str, data_dir: str = 'data') -> xr.DataArray:
    """
    Load cached daily Tmin DataArray (time, lat, lon) for a named city.

    Raises FileNotFoundError if 01b_data_acquisition_tmin has not been run.
    """
    path = Path(data_dir) / f'{name}_tmin.nc'
    if not path.exists():
        raise FileNotFoundError(
            f'Cache not found: {path}\nRun 01b_data_acquisition_tmin.ipynb first.'
        )
    da = xr.open_dataset(path)['tmin'].load()
    print(f'{name}: shape {dict(zip(da.dims, da.shape))}  '
          f'{str(da.time.values[0])[:10]} to {str(da.time.values[-1])[:10]}')
    return da


def compute_tx90p_threshold(
    da: xr.DataArray,
    window: int = 5,
    per: Union[int, list] = 90,
) -> xr.DataArray:
    """
    Calendar-day percentile threshold using a centred moving window (ETCCDI definition).

    For each of the 365 calendar days, the percentile(s) in `per` are estimated
    from values within a centred `window`-day window pooled across all years in `da`.

    Parameters
    ----------
    da : DataArray (time, lat, lon). Must have a 'units' attribute ('degC').
    window : width of the centred day-of-year window (default 5 = ±2 days).
    per : single percentile or list (e.g. [90, 95, 99]).
          Multiple percentiles are stacked along a 'percentile' dimension.

    Returns
    -------
    DataArray (dayofyear, lat, lon) for a scalar `per`, or
    (percentile, dayofyear, lat, lon) for a list.  Units 'degC'.
    """
    import xclim.core.calendar

    da = da.copy()
    da.attrs.setdefault('units', 'degC')

    scalar   = isinstance(per, int)
    per_list = [per] if scalar else list(per)

    layers = []
    for p in per_list:
        thresh = xclim.core.calendar.percentile_doy(da, window=window, per=p)
        thresh = thresh.squeeze('percentiles', drop=True)
        layers.append(thresh)

    if scalar:
        result = layers[0]
        result.attrs['percentile'] = per
    else:
        result = xr.concat(layers, dim=pd.Index(per_list, name='percentile'))

    result.attrs['units']  = 'degC'
    result.attrs['window'] = window
    return result


def load_tx90p_threshold(name: str, data_dir: str = 'data') -> xr.DataArray:
    """
    Load cached calendar-day TX percentile threshold DataArray.

    Returns DataArray (percentile, dayofyear, lat, lon) when multiple
    percentiles were saved, or (dayofyear, lat, lon) for a single percentile.

    Raises FileNotFoundError if 02_compute_baselines has not been run.
    """
    path = Path(data_dir) / f'{name}_tx90p_thresh.nc'
    if not path.exists():
        raise FileNotFoundError(
            f'TX90p threshold not found: {path}\nRun 02_compute_baselines.ipynb first.'
        )
    da = xr.open_dataset(path)['tmax'].load()
    window = da.attrs.get('window', 5)
    pcts   = da.percentile.values.tolist() if 'percentile' in da.dims else da.attrs.get('percentile', '?')
    print(f'{name} TX90p threshold: shape {dict(zip(da.dims, da.shape))}  '
          f'window={window}  percentiles={pcts}  '
          f'range {float(da.min()):.1f}–{float(da.max()):.1f} °C')
    return da


def load_tn90p_threshold(name: str, data_dir: str = 'data') -> xr.DataArray:
    """
    Load cached calendar-day TN percentile threshold DataArray.

    Raises FileNotFoundError if 02_compute_baselines has not been run.
    """
    path = Path(data_dir) / f'{name}_tn90p_thresh.nc'
    if not path.exists():
        raise FileNotFoundError(
            f'TN90p threshold not found: {path}\nRun 02_compute_baselines.ipynb first.'
        )
    da = xr.open_dataset(path)['tmin'].load()
    window = da.attrs.get('window', 5)
    pcts   = da.percentile.values.tolist() if 'percentile' in da.dims else da.attrs.get('percentile', '?')
    print(f'{name} TN90p threshold: shape {dict(zip(da.dims, da.shape))}  '
          f'window={window}  percentiles={pcts}  '
          f'range {float(da.min()):.1f}–{float(da.max()):.1f} °C')
    return da


def load_baseline(name: str, data_dir: str = 'data') -> xr.DataArray:
    """
    Load cached per-pixel Tmax baseline DataArray (percentile, lat, lon) for a named city.

    Raises FileNotFoundError if 02_compute_baselines has not been run.
    """
    path = Path(data_dir) / f'{name}_baseline.nc'
    if not path.exists():
        raise FileNotFoundError(
            f'Baseline not found: {path}\nRun 02_compute_baselines.ipynb first.'
        )
    da = xr.open_dataset(path)['tmax'].load()
    print(f'{name} baseline: percentiles {da.percentile.values.tolist()}, '
          f'shape {dict(zip(da.dims, da.shape))}')
    return da


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def count_threshold_days(da: xr.DataArray, threshold: float) -> xr.DataArray:
    """
    Count days where Tmax exceeds `threshold` along the time dimension.

    Parameters
    ----------
    da : DataArray with a 'time' dimension. May be (time,) or (time, lat, lon).
    threshold : temperature threshold in °C.

    Returns
    -------
    DataArray with the time dimension reduced; spatial dims preserved if present.
    """
    return (da > threshold).sum(dim='time')


def percentile_baseline(
    da: xr.DataArray,
    percentile: Union[int, float, list],
) -> xr.DataArray:
    """
    Compute per-pixel historical Tmax percentile(s) over the full time record.

    Parameters
    ----------
    da : DataArray (time, lat, lon).
    percentile : single value or list of values in [0, 100].

    Returns
    -------
    DataArray with dims (percentile, lat, lon) for multiple percentiles, or
    (lat, lon) for a single percentile value.
    """
    scalar = not hasattr(percentile, '__iter__')
    pct_list = [percentile] if scalar else list(percentile)
    q = [p / 100.0 for p in pct_list]

    result = da.quantile(q, dim='time')
    # Replace float quantile coords (0.9) with integer percentile labels (90)
    result = result.assign_coords(quantile=pct_list).rename({'quantile': 'percentile'})

    if scalar:
        result = result.squeeze('percentile', drop=True)
    return result


def threshold_sensitivity_curve(
    da: xr.DataArray,
    threshold_range: Iterable[float],
) -> pd.DataFrame:
    """
    Compute heat day statistics across a range of absolute thresholds.

    Spatially averages `da` first so the result is a city-wide summary.

    Parameters
    ----------
    da : DataArray (time, lat, lon) or (time,).
    threshold_range : iterable of threshold values in °C.

    Returns
    -------
    DataFrame with columns: threshold, heat_days_per_year, pct_days.
    """
    ts = da.mean(dim=['lat', 'lon']) if 'lat' in da.dims else da
    n_years = float(np.unique(ts.time.dt.year.values).size)
    n_days = float(ts.sizes['time'])

    records = []
    for thr in threshold_range:
        hd = int((ts > thr).sum().item())
        records.append({
            'threshold':        thr,
            'heat_days_per_year': hd / n_years,
            'pct_days':         100.0 * hd / n_days,
        })
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Spatial analysis
# ---------------------------------------------------------------------------

def compute_absolute_heat_days(
    da: xr.DataArray, year: int, threshold: float = 30.0
) -> xr.DataArray:
    """
    Per-pixel count of days where Tmax >= threshold in a given year.

    Parameters
    ----------
    da : DataArray (time, lat, lon).
    year : calendar year to subset.
    threshold : absolute temperature threshold in °C.
    """
    da_year = da.sel(time=da.time.dt.year == year)
    return (da_year >= threshold).sum(dim='time').rename('abs_heat_days')


def compute_relative_heat_days(
    da: xr.DataArray,
    year: int,
    threshold: Union[float, xr.DataArray],
) -> xr.DataArray:
    """
    Per-pixel count of days where Tmax exceeds a relative threshold in a given year.

    Parameters
    ----------
    da : DataArray (time, lat, lon).
    year : calendar year to subset.
    threshold : scalar float or per-pixel DataArray (lat, lon). If a DataArray is
                passed (e.g. the 90th percentile layer from load_baseline()), each
                pixel is compared against its own local threshold.
    """
    da_year = da.sel(time=da.time.dt.year == year)
    return (da_year > threshold).sum(dim='time').rename('rel_heat_days')


def _point_in_poly_mask(
    poly, lon_flat: np.ndarray, lat_flat: np.ndarray
) -> np.ndarray:
    """Vectorised point-in-polygon, compatible with Shapely 1.x and 2.x."""
    try:
        import shapely
        if int(shapely.__version__.split('.')[0]) >= 2:
            from shapely import contains_xy
            return contains_xy(poly, lon_flat, lat_flat)
    except Exception:
        pass
    from shapely.geometry import Point
    return np.array([poly.contains(Point(x, y)) for x, y in zip(lon_flat, lat_flat)])


def aggregate_to_neighbourhoods(
    heat_day_map: xr.DataArray,
    gdf: gpd.GeoDataFrame,
    col: str = 'mean_heat_days',
) -> gpd.GeoDataFrame:
    """
    Average per-pixel heat-day counts within each neighbourhood polygon.

    Parameters
    ----------
    heat_day_map : 2-D DataArray (lat, lon) — output of compute_*_heat_days().
    gdf : GeoDataFrame with 'name' and 'geometry' columns.
    col : name for the new column added to the returned GeoDataFrame.

    Returns
    -------
    Copy of gdf with a new column `col` containing mean heat days per neighbourhood.
    Neighbourhoods with no overlapping pixels receive NaN.
    """
    lats = heat_day_map.lat.values
    lons = heat_day_map.lon.values
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    lon_flat = lon_grid.ravel()
    lat_flat = lat_grid.ravel()
    val_flat = heat_day_map.values.ravel().astype(float)

    means = []
    for _, row in gdf.iterrows():
        mask = _point_in_poly_mask(row.geometry, lon_flat, lat_flat)
        valid = val_flat[mask]
        valid = valid[~np.isnan(valid)]
        if len(valid) > 0:
            means.append(float(valid.mean()))
        else:
            # No pixel centroid inside polygon — fall back to nearest pixel
            cx, cy = row.geometry.centroid.x, row.geometry.centroid.y
            dist2  = (lon_flat - cx) ** 2 + (lat_flat - cy) ** 2
            nearest_val = val_flat[np.argmin(dist2)]
            means.append(float(nearest_val) if not np.isnan(nearest_val) else np.nan)

    result = gdf.copy()
    result[col] = means
    return result


# ---------------------------------------------------------------------------
# Neighbourhood boundaries
# ---------------------------------------------------------------------------

def _normalise_name_col(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Standardise the neighbourhood label column to 'name'."""
    if 'name' in gdf.columns and gdf['name'].notna().any():
        return gdf
    candidates = [
        'name_neighborhood', 'name_subdistrict', 'nome',
        'bairro', 'NM_BAIRRO', 'NOME',
    ]
    name_col = next(
        (c for c in candidates if c in gdf.columns and gdf[c].notna().any()), None
    )
    gdf = gdf.copy()
    fallback = [f'Zone-{i+1:02d}' for i in range(len(gdf))]
    if name_col:
        gdf['name'] = gdf[name_col].fillna(pd.Series(fallback, index=gdf.index))
    else:
        gdf['name'] = fallback
    return gdf


def _synthetic_grid(
    bbox: dict, grid_shape: tuple = (5, 5)
) -> gpd.GeoDataFrame:
    from shapely.geometry import box as shapely_box
    rows, cols = grid_shape
    lats = np.linspace(bbox['south'], bbox['north'], rows + 1)
    lons = np.linspace(bbox['west'],  bbox['east'],  cols + 1)
    records = []
    n = 1
    for r in range(rows):
        for c in range(cols):
            records.append({
                'name': f'N-{n:02d}',
                'geometry': shapely_box(lons[c], lats[r], lons[c + 1], lats[r + 1]),
            })
            n += 1
    print(f'Using synthetic {rows}x{cols} grid ({len(records)} dummy neighbourhoods).')
    return gpd.GeoDataFrame(records, crs='EPSG:4326')


def load_neighbourhood_boundaries(
    city: str,
    data_dir: str = 'data',
    source: str = 'geobr',
) -> gpd.GeoDataFrame:
    """
    Load neighbourhood boundaries for a named city.

    Parameters
    ----------
    city : key in CITIES ('salvador', 'teresina', 'caceres').
    data_dir : directory for the geobr cache file.
    source : 'geobr' downloads from geobr and caches locally (default);
             'synthetic' returns a 5x5 dummy grid (no download);
             or a file path to a local GeoJSON / Shapefile / GeoPackage.

    Returns
    -------
    GeoDataFrame with columns ['name', 'geometry'], CRS EPSG:4326.
    """
    if city not in CITIES:
        raise ValueError(f"Unknown city '{city}'. Add it to CITIES in utils/heat.py.")

    cfg = CITIES[city]
    cache_path = _GEOBR_CACHE_TPL.format(data_dir=data_dir, city=city)

    if source == 'synthetic':
        return _synthetic_grid(cfg['bbox'])

    if source == 'geobr':
        if os.path.exists(cache_path):
            gdf = gpd.read_file(cache_path)
            print(f'Loaded {len(gdf)} neighbourhoods from cache: {cache_path}')
        else:
            from geobr import read_neighborhood
            ibge_code = cfg['ibge_code']
            print(f'Downloading boundaries from geobr for {cfg["label"]} '
                  f'(IBGE {ibge_code}) ...')
            gdf_all = read_neighborhood(year=2010, simplified=True)
            gdf = gdf_all[gdf_all['code_muni'] == ibge_code].copy()
            if gdf.empty:
                raise ValueError(
                    f'geobr returned no neighbourhoods for IBGE code {ibge_code}. '
                    f'Try source="synthetic" as a fallback.'
                )
            if gdf.crs and gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs('EPSG:4326')
            os.makedirs(data_dir, exist_ok=True)
            gdf.to_file(cache_path, driver='GPKG')
            print(f'Cached to {cache_path}')
        gdf = _normalise_name_col(gdf)
        return gdf[['name', 'geometry']]

    if os.path.exists(source):
        gdf = gpd.read_file(source)
        if gdf.crs is None:
            gdf = gdf.set_crs('EPSG:4326')
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs('EPSG:4326')
        gdf = _normalise_name_col(gdf)
        print(f'Loaded {len(gdf)} neighbourhoods from {source}.')
        return gdf[['name', 'geometry']]

    raise ValueError(
        f"Cannot resolve source '{source}'. "
        "Use 'geobr', 'synthetic', or a valid file path."
    )


# ---------------------------------------------------------------------------
# GEE extraction  (called only from 01_data_acquisition)
# ---------------------------------------------------------------------------

def _pivot_to_xarray(df: pd.DataFrame, varname: str) -> xr.DataArray:
    """Pivot a flat GEE DataFrame (date, lat, lon, value) to xr.DataArray (time, lat, lon)."""
    df = df.copy()
    df['latitude']  = df['latitude'].round(4)
    df['longitude'] = df['longitude'].round(4)
    df['date']      = pd.to_datetime(df['date'])

    pivot = df.pivot_table(
        index='date', columns=['latitude', 'longitude'],
        values=varname, aggfunc='mean',
    )
    lats  = sorted(pivot.columns.get_level_values(0).unique())
    lons  = sorted(pivot.columns.get_level_values(1).unique())
    times = pivot.index.values

    arr = np.full((len(times), len(lats), len(lons)), np.nan, dtype=np.float32)
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            if (lat, lon) in pivot.columns:
                arr[:, i, j] = pivot[(lat, lon)].values

    return xr.DataArray(
        arr,
        dims=['time', 'lat', 'lon'],
        coords={'time': times, 'lat': lats, 'lon': lons},
        name=varname,
        attrs={'units': 'degC', 'source': 'GSHTD / Zhang et al. (2022)'},
    )


def extract_city_tmax(
    city: str,
    data_dir: str,
    start: str,
    end: str,
    resolution: int = 1000,
    force_refresh: bool = False,
) -> None:
    """
    Download daily Tmax from GSHTD (Zhang et al. 2022) via GEE for a named city.

    Data are pulled in 90-day chunks to stay within GEE memory limits. On
    subsequent runs the existing cache is kept unless force_refresh=True.

    Parameters
    ----------
    city : key in CITIES registry ('salvador', 'teresina', 'caceres').
    data_dir : directory to write the NetCDF cache.
    start, end : ISO date strings, e.g. '2003-01-01' and '2020-12-31'.
    resolution : GEE extraction scale in metres (default 1000).
    force_refresh : if True, re-download even if a cache file already exists.

    Output
    ------
    Writes `{data_dir}/{city}_tmax.nc` — an xr.Dataset with a single variable
    'tmax' of shape (time, lat, lon).
    """
    import ee

    if city not in CITIES:
        raise ValueError(f"Unknown city '{city}'. Add it to CITIES in utils/heat.py.")

    cfg      = CITIES[city]
    out_path = Path(data_dir) / f'{city}_tmax.nc'

    if out_path.exists() and not force_refresh:
        print(f'Cache exists: {out_path}  (pass force_refresh=True to re-download)')
        return

    bbox = cfg['bbox']
    roi  = ee.Geometry.Rectangle(
        [bbox['west'], bbox['south'], bbox['east'], bbox['north']]
    )

    filtered = (
        ee.ImageCollection(cfg['gee_collection'])
        .filterDate(start, end)
        .filterBounds(roi)
        .filter(ee.Filter.eq('prop_type', 'tmax'))
    )
    n_images = filtered.size().getInfo()
    print(f'{cfg["label"]}: {n_images} TMAX images in GEE '
          f'({start} to {end})')

    t0 = datetime.strptime(start, '%Y-%m-%d')
    t1 = datetime.strptime(end,   '%Y-%m-%d')
    chunks = []
    cur = t0

    while cur <= t1:
        chunk_end = min(cur + timedelta(days=90), t1)
        col_chunk = filtered.filterDate(
            cur.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d')
        )
        if col_chunk.size().getInfo() == 0:
            cur = chunk_end + timedelta(days=1)
            continue

        processed = col_chunk.map(lambda img:
            img.select('b1').divide(10).rename('tmax')
               .clip(roi).copyProperties(img, ['system:time_start'])
        )
        try:
            raw = processed.getRegion(
                geometry=roi, scale=resolution, crs='EPSG:4326'
            ).getInfo()
            if len(raw) > 1:
                df = pd.DataFrame(raw[1:], columns=raw[0])
                df['time']      = pd.to_datetime(df['time'], unit='ms')
                df['date']      = df['time'].dt.date
                df              = df.dropna(subset=['tmax'])
                df['latitude']  = df['latitude'].astype(float)
                df['longitude'] = df['longitude'].astype(float)
                df['tmax']      = df['tmax'].astype(float)
                chunks.append(df)
                print(f'  {cur.date()} – {chunk_end.date()}: {len(df):,} rows')
        except Exception as exc:
            print(f'  Chunk failed ({cur.date()}): {exc}')

        cur = chunk_end + timedelta(days=1)

    if not chunks:
        raise RuntimeError(
            f'GEE returned no data for {city}. Check ROI, date range, and credentials.'
        )

    da = _pivot_to_xarray(pd.concat(chunks, ignore_index=True), 'tmax')
    os.makedirs(data_dir, exist_ok=True)
    da.to_dataset().to_netcdf(out_path)
    print(f'Saved: {out_path}  '
          f'({da.sizes["time"]} days, {da.sizes["lat"]}x{da.sizes["lon"]} pixels)')


def extract_city_tmin(
    city: str,
    data_dir: str,
    start: str,
    end: str,
    resolution: int = 1000,
    force_refresh: bool = False,
) -> None:
    """
    Download daily Tmin from GSHTD (Zhang et al. 2022) via GEE for a named city.

    Identical to extract_city_tmax but filters prop_type='tmin' and writes
    `{data_dir}/{city}_tmin.nc` with variable 'tmin'.
    """
    import ee

    if city not in CITIES:
        raise ValueError(f"Unknown city '{city}'. Add it to CITIES in utils/heat.py.")

    cfg      = CITIES[city]
    out_path = Path(data_dir) / f'{city}_tmin.nc'

    if out_path.exists() and not force_refresh:
        print(f'Cache exists: {out_path}  (pass force_refresh=True to re-download)')
        return

    bbox = cfg['bbox']
    roi  = ee.Geometry.Rectangle(
        [bbox['west'], bbox['south'], bbox['east'], bbox['north']]
    )

    filtered = (
        ee.ImageCollection(cfg['gee_collection'])
        .filterDate(start, end)
        .filterBounds(roi)
        .filter(ee.Filter.eq('prop_type', 'tmin'))
    )
    n_images = filtered.size().getInfo()
    print(f'{cfg["label"]}: {n_images} TMIN images in GEE '
          f'({start} to {end})')

    t0 = datetime.strptime(start, '%Y-%m-%d')
    t1 = datetime.strptime(end,   '%Y-%m-%d')
    chunks = []
    cur = t0

    while cur <= t1:
        chunk_end = min(cur + timedelta(days=90), t1)
        col_chunk = filtered.filterDate(
            cur.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d')
        )
        if col_chunk.size().getInfo() == 0:
            cur = chunk_end + timedelta(days=1)
            continue

        processed = col_chunk.map(lambda img:
            img.select('b1').divide(10).rename('tmin')
               .clip(roi).copyProperties(img, ['system:time_start'])
        )
        try:
            raw = processed.getRegion(
                geometry=roi, scale=resolution, crs='EPSG:4326'
            ).getInfo()
            if len(raw) > 1:
                df = pd.DataFrame(raw[1:], columns=raw[0])
                df['time']      = pd.to_datetime(df['time'], unit='ms')
                df['date']      = df['time'].dt.date
                df              = df.dropna(subset=['tmin'])
                df['latitude']  = df['latitude'].astype(float)
                df['longitude'] = df['longitude'].astype(float)
                df['tmin']      = df['tmin'].astype(float)
                chunks.append(df)
                print(f'  {cur.date()} – {chunk_end.date()}: {len(df):,} rows')
        except Exception as exc:
            print(f'  Chunk failed ({cur.date()}): {exc}')

        cur = chunk_end + timedelta(days=1)

    if not chunks:
        raise RuntimeError(
            f'GEE returned no data for {city}. Check ROI, date range, and credentials.'
        )

    da = _pivot_to_xarray(pd.concat(chunks, ignore_index=True), 'tmin')
    os.makedirs(data_dir, exist_ok=True)
    da.to_dataset().to_netcdf(out_path)
    print(f'Saved: {out_path}  '
          f'({da.sizes["time"]} days, {da.sizes["lat"]}x{da.sizes["lon"]} pixels)')


# ---------------------------------------------------------------------------
# Population / person-days helpers
# ---------------------------------------------------------------------------

def extract_city_population(
    city: str,
    data_dir: str,
    start_year: int = 2003,
    end_year: int = 2020,
    resolution: int = 100,
    force_refresh: bool = False,
) -> None:
    """
    Download annual WorldPop 100m total population for a named city from GEE.

    Uses collection WorldPop/GP/100m/pop (total population, multiple years).
    One image is extracted per year; all years are stacked into a single
    NetCDF with dimensions (year, lat, lon).

    Output
    ------
    Writes `{data_dir}/{city}_population.nc` — xr.Dataset variable 'population'.
    """
    import ee

    if city not in CITIES:
        raise ValueError(f"Unknown city '{city}'.")

    cfg      = CITIES[city]
    out_path = Path(data_dir) / f'{city}_population.nc'

    if out_path.exists() and not force_refresh:
        print(f'Cache exists: {out_path}  (pass force_refresh=True to re-download)')
        return

    bbox = cfg['bbox']
    roi  = ee.Geometry.Rectangle(
        [bbox['west'], bbox['south'], bbox['east'], bbox['north']]
    )

    collection = ee.ImageCollection('WorldPop/GP/100m/pop').filter(
        ee.Filter.eq('country', 'BRA')
    )

    # Verify which years are actually available before looping
    available = sorted(collection.aggregate_array('year').distinct().getInfo())
    print(f'{cfg["label"]}: WorldPop years available — {available}')

    year_arrays = []
    years_found = []
    for yr in range(start_year, end_year + 1):
        yr_col = collection.filter(ee.Filter.eq('year', yr))
        if yr not in available:
            nearest = min(available, key=lambda y: abs(y - yr))
            print(f'  {yr}: not found — using {nearest} as proxy')
            yr_col = collection.filter(ee.Filter.eq('year', nearest))

        img_col = yr_col.select('population').map(lambda i: i.clip(roi))
        try:
            raw = img_col.getRegion(geometry=roi, scale=resolution, crs='EPSG:4326').getInfo()
            if len(raw) > 1:
                df = pd.DataFrame(raw[1:], columns=raw[0])
                df = df.dropna(subset=['population'])
                df['latitude']   = df['latitude'].astype(float).round(4)
                df['longitude']  = df['longitude'].astype(float).round(4)
                df['population'] = df['population'].astype(float)
                # Build 2-D (lat, lon) array directly — no time dimension needed
                lats = sorted(df['latitude'].unique())
                lons = sorted(df['longitude'].unique())
                arr  = np.full((len(lats), len(lons)), np.nan, dtype=np.float32)
                li   = {v: i for i, v in enumerate(lats)}
                lj   = {v: i for i, v in enumerate(lons)}
                for _, r in df.iterrows():
                    arr[li[r['latitude']], lj[r['longitude']]] = r['population']
                da = xr.DataArray(
                    arr, dims=['lat', 'lon'],
                    coords={'lat': lats, 'lon': lons},
                    name='population',
                )
                year_arrays.append(da)
                years_found.append(yr)
                print(f'  {yr}: {len(df):,} pixels')
        except Exception as exc:
            print(f'  {yr}: extraction failed — {exc}')

    if not year_arrays:
        raise RuntimeError(f'No population data extracted for {city}.')

    combined = xr.concat(year_arrays, dim=pd.Index(years_found, name='year'))
    os.makedirs(data_dir, exist_ok=True)
    combined.to_dataset().to_netcdf(out_path)
    print(f'Saved: {out_path}  ({len(years_found)} years, '
          f'{combined.sizes["lat"]}x{combined.sizes["lon"]} pixels)')


def load_population(name: str, data_dir: str = 'data') -> xr.DataArray:
    """Load cached annual population DataArray (year, lat, lon) for a named city."""
    path = Path(data_dir) / f'{name}_population.nc'
    if not path.exists():
        raise FileNotFoundError(
            f'Cache not found: {path}\nRun 01_data_acquisition population section first.'
        )
    da = xr.open_dataset(path)['population']
    print(f'{name} population: years {int(da.year.min())}–{int(da.year.max())}, '
          f'shape {dict(zip(da.dims, da.shape))}')
    return da


def resample_population_to_grid(
    pop_da: xr.DataArray,
    target_da: xr.DataArray,
) -> xr.DataArray:
    """
    Sum 100m WorldPop pixels onto a coarser target grid (e.g. 1km GSHTD grid).

    Each target cell receives the sum of all population pixels whose centres
    fall within its extent.  This preserves total population (head-count).

    Parameters
    ----------
    pop_da   : 2-D DataArray (lat, lon) at ~100m.
    target_da: any DataArray sharing the target (lat, lon) grid.

    Returns
    -------
    2-D DataArray (lat, lon) of summed population on the target grid.
    """
    tlats = target_da.lat.values
    tlons = target_da.lon.values
    dlat  = abs(float(tlats[1] - tlats[0])) / 2
    dlon  = abs(float(tlons[1] - tlons[0])) / 2

    plats = pop_da.lat.values
    plons = pop_da.lon.values
    pvals = pop_da.values

    result = np.zeros((len(tlats), len(tlons)), dtype=np.float64)

    for i, tlat in enumerate(tlats):
        lat_mask = (plats >= tlat - dlat) & (plats < tlat + dlat)
        if not lat_mask.any():
            continue
        pslice = pvals[lat_mask, :]
        for j, tlon in enumerate(tlons):
            lon_mask = (plons >= tlon - dlon) & (plons < tlon + dlon)
            if lon_mask.any():
                result[i, j] = np.nansum(pslice[:, lon_mask])

    return xr.DataArray(
        result,
        coords={'lat': tlats, 'lon': tlons},
        dims=['lat', 'lon'],
        name='population',
    )


def compute_person_days_map(
    heat_day_map: xr.DataArray,
    pop_grid: xr.DataArray,
) -> xr.DataArray:
    """
    Pixel-wise product of heat-day count and population on the same grid.

    Parameters
    ----------
    heat_day_map : 2-D DataArray (lat, lon) — output of compute_*_heat_days().
    pop_grid     : 2-D DataArray (lat, lon) — population resampled to the same grid.

    Returns
    -------
    2-D DataArray (lat, lon) of person-days.
    """
    return (heat_day_map * pop_grid).rename('person_days')


def aggregate_person_days_to_neighbourhoods(
    person_days_map: xr.DataArray,
    gdf: gpd.GeoDataFrame,
    col: str = 'total_person_days',
) -> gpd.GeoDataFrame:
    """
    Sum per-pixel person-days within each neighbourhood polygon.

    Uses sum (not mean) because person-days are an extensive quantity —
    a larger neighbourhood should show higher total exposure.
    Polygons with no overlapping pixels fall back to the nearest pixel.
    """
    lats     = person_days_map.lat.values
    lons     = person_days_map.lon.values
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    lon_flat = lon_grid.ravel()
    lat_flat = lat_grid.ravel()
    val_flat = person_days_map.values.ravel().astype(float)

    totals = []
    for _, row in gdf.iterrows():
        mask  = _point_in_poly_mask(row.geometry, lon_flat, lat_flat)
        valid = val_flat[mask]
        valid = valid[~np.isnan(valid)]
        if len(valid) > 0:
            totals.append(float(valid.sum()))
        else:
            cx, cy   = row.geometry.centroid.x, row.geometry.centroid.y
            dist2    = (lon_flat - cx) ** 2 + (lat_flat - cy) ** 2
            nearest  = val_flat[np.argmin(dist2)]
            totals.append(float(nearest) if not np.isnan(nearest) else np.nan)

    result      = gdf.copy()
    result[col] = totals
    return result


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def plot_person_days_maps(
    da: xr.DataArray,
    gdf: gpd.GeoDataFrame,
    year: int,
    percentile: int,
    baseline: xr.DataArray,
    pop_grid: xr.DataArray,
    threshold: float = 30.0,
    city_name: str = '',
) -> tuple:
    """
    Side-by-side choropleth maps: absolute vs relative person-days per neighbourhood.

    Parameters
    ----------
    da : (time, lat, lon) Tmax DataArray.
    gdf : neighbourhood GeoDataFrame with 'name' and 'geometry'.
    year : calendar year to analyse.
    percentile : integer percentile label for the relative threshold.
    baseline : per-pixel baseline DataArray (percentile, lat, lon).
    pop_grid : 2-D population DataArray (lat, lon) on the same 1km grid as da.
    threshold : absolute temperature threshold in °C.
    city_name : city label for the figure suptitle.

    Returns
    -------
    (abs_pd_nbhd, rel_pd_nbhd) — GeoDataFrames with 'total_person_days' column.
    """
    import matplotlib.cm as mcm
    import matplotlib.patches as mpatches

    rel_thr  = baseline.sel(percentile=percentile)
    abs_map  = compute_absolute_heat_days(da, year, threshold)
    rel_map  = compute_relative_heat_days(da, year, rel_thr)

    pd_abs   = compute_person_days_map(abs_map, pop_grid)
    pd_rel   = compute_person_days_map(rel_map, pop_grid)

    abs_nbhd = aggregate_person_days_to_neighbourhoods(pd_abs, gdf)
    rel_nbhd = aggregate_person_days_to_neighbourhoods(pd_rel, gdf)

    cmap_obj = mcm.get_cmap('YlOrRd')
    pct_temp = float(baseline.sel(percentile=percentile).mean())
    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    panels = [
        (abs_nbhd, axes[0], f'Absolute: Tmax >= {threshold:.0f} C  ({year})'),
        (rel_nbhd, axes[1], f'Relative: {percentile}th pct baseline ({pct_temp:.1f} \u00b0C)  ({year})'),
    ]
    for nbhd_gdf, ax, title in panels:
        series  = nbhd_gdf['total_person_days']
        working = nbhd_gdf.copy()

        working['_rank'] = series.rank(pct=True, method='first', na_option='keep')

        working.plot(
            column='_rank', ax=ax, cmap='YlOrRd',
            vmin=0, vmax=1,
            edgecolor='black', linewidth=0.4,
            legend=False,
            missing_kwds={'color': 'lightgrey', 'edgecolor': 'black', 'linewidth': 0.4},
        )

        valid_idx     = working['_rank'].dropna().index
        ranked_series = series.loc[valid_idx].sort_values()
        n_valid       = len(ranked_series)
        handles       = []
        for i in range(5):
            lo_i = int(i * n_valid / 5)
            hi_i = int((i + 1) * n_valid / 5)
            band = ranked_series.iloc[lo_i:hi_i]
            lo_v, hi_v = band.min(), band.max()
            handles.append(mpatches.Patch(
                facecolor=cmap_obj((i * 2 + 1) / 10),
                label=f'{lo_v:,.0f}\u2013{hi_v:,.0f} pd',
            ))
        n_nan = series.isna().sum()
        if n_nan:
            handles.append(mpatches.Patch(facecolor='lightgrey', label=f'No data ({n_nan})'))
        ax.legend(handles=handles, title='Person-days\n(quintile rank)',
                  fontsize=7, title_fontsize=7, loc='lower left')
        for _, row in nbhd_gdf.iterrows():
            cx, cy = row.geometry.centroid.x, row.geometry.centroid.y
            ax.annotate(
                row['name'], xy=(cx, cy), ha='center', va='center',
                fontsize=6.5, color='black',
                bbox=dict(boxstyle='round,pad=0.1', fc='white', alpha=0.5, lw=0),
            )
        ax.set_title(title, fontsize=10)
        ax.set_aspect('equal')

    suptitle = (f'Neighbourhood heat person-days \u2014 {city_name} {year}'
                if city_name else f'Heat person-days {year}')
    fig.suptitle(suptitle, fontsize=13)
    plt.tight_layout()
    plt.show()
    return abs_nbhd, rel_nbhd


def plot_person_days_quadrant(
    abs_pd_nbhd: gpd.GeoDataFrame,
    rel_pd_nbhd: gpd.GeoDataFrame,
    year: int,
    percentile: int,
    city_name: str = '',
) -> None:
    """
    Neighbourhood rank quadrant scatter: absolute vs relative person-day rank.

    Rank 1 = most person-days. Axes inverted so high-burden neighbourhoods
    appear at top-right.

    Parameters
    ----------
    abs_pd_nbhd : GeoDataFrame with 'name' and 'total_person_days' — absolute counts.
    rel_pd_nbhd : GeoDataFrame with 'name' and 'total_person_days' — relative counts.
    year : calendar year (for the title).
    percentile : relative-threshold percentile (for the y-axis label).
    city_name : city label for the title.
    """
    merged = (
        abs_pd_nbhd[['name', 'total_person_days']]
        .copy()
        .rename(columns={'total_person_days': 'abs_pd'})
    )
    merged['rel_pd'] = rel_pd_nbhd['total_person_days'].values
    merged = merged.dropna(subset=['abs_pd', 'rel_pd']).reset_index(drop=True)

    n = len(merged)
    if n < 2:
        print('Too few neighbourhoods with data to plot.')
        return

    merged['abs_rank'] = merged['abs_pd'].rank(ascending=False, method='min').astype(int)
    merged['rel_rank'] = merged['rel_pd'].rank(ascending=False, method='min').astype(int)
    rho, pval = spearmanr(merged['abs_rank'], merged['rel_rank'])
    med = (n + 1) / 2

    fig, ax = plt.subplots(figsize=(9, 9))
    ax.scatter(merged['abs_rank'], merged['rel_rank'],
               s=80, color='steelblue', zorder=3, alpha=0.85)
    for _, row in merged.iterrows():
        ax.annotate(
            row['name'], (row['abs_rank'], row['rel_rank']),
            xytext=(5, 3), textcoords='offset points',
            fontsize=8, color='#222222',
        )

    ax.plot([1, n], [1, n], 'k--', linewidth=1, alpha=0.4)
    ax.axvline(med, color='grey', linestyle=':', linewidth=1, alpha=0.7)
    ax.axhline(med, color='grey', linestyle=':', linewidth=1, alpha=0.7)
    ax.invert_xaxis()
    ax.invert_yaxis()

    pad = n * 0.04
    quadrant_labels = [
        (1 + pad, 1 + pad, 'left',  'top',    'Robust priorities', '#c0392b', '#fdecea'),
        (n - pad, 1 + pad, 'right', 'top',    'Chronic burden',    '#e67e22', '#fef9e7'),
        (1 + pad, n - pad, 'left',  'bottom', 'Emerging concern',  '#2980b9', '#eaf4fb'),
        (n - pad, n - pad, 'right', 'bottom', 'Lower priority',    '#27ae60', '#eafaf1'),
    ]
    for x, y, ha, va, txt, fg, bg in quadrant_labels:
        ax.text(x, y, txt, ha=ha, va=va, fontsize=9, color=fg,
                bbox=dict(boxstyle='round,pad=0.25', fc=bg, alpha=0.8))

    ax.set_xlabel('Rank \u2014 absolute threshold (1 = most person-days)', fontsize=11)
    ax.set_ylabel(f'Rank \u2014 {percentile}th pct relative threshold (1 = most)', fontsize=11)
    title = f'Neighbourhood person-day ranks: absolute vs relative\n'
    title += f'{city_name + " " if city_name else ""}{year}  |  {n} neighbourhoods'
    ax.set_title(title, fontsize=12)
    ax.grid(True, alpha=0.2)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.tight_layout()
    plt.show()

    p_str = f'{pval:.3f}' if pval >= 0.001 else '<0.001'
    print(f'Spearman rho = {rho:.3f}  (p = {p_str},  n = {n})')


def plot_population_heat_scatter(
    abs_nbhd: gpd.GeoDataFrame,
    rel_nbhd: gpd.GeoDataFrame,
    pop_nbhd: gpd.GeoDataFrame,
    year: int,
    percentile: int,
    city_name: str = '',
    top_n: int = 5,
) -> None:
    """
    Scatter of neighbourhood population vs mean heat days — two panels (abs / rel).

    Reveals which neighbourhoods combine large populations with high heat exposure.
    Median lines divide each panel into four quadrants; the top-right `top_n`
    neighbourhoods (highest combined population + heat rank) are labelled.

    Parameters
    ----------
    abs_nbhd : GeoDataFrame with 'name' and 'mean_heat_days' — absolute threshold.
    rel_nbhd : GeoDataFrame with 'name' and 'mean_heat_days' — relative threshold.
    pop_nbhd : GeoDataFrame with 'name' and 'total_person_days' used as neighbourhood population.
    year : calendar year (for the title).
    percentile : relative-threshold percentile used (for the right panel title).
    city_name : city label for the figure suptitle.
    top_n : number of top-right neighbourhoods to annotate.
    """
    pop_s = pop_nbhd.set_index('name')['total_person_days']

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    panels = [
        (abs_nbhd, axes[0], f'Absolute threshold  ({year})'),
        (rel_nbhd, axes[1], f'{percentile}th pct relative threshold  ({year})'),
    ]

    for nbhd_gdf, ax, title in panels:
        merged = nbhd_gdf[['name', 'mean_heat_days']].copy()
        merged['population'] = merged['name'].map(pop_s)
        merged = merged.dropna().reset_index(drop=True)

        ax.scatter(merged['population'], merged['mean_heat_days'],
                   s=60, color='steelblue', alpha=0.7, zorder=3)

        merged['_pr'] = merged['population'].rank(ascending=False)
        merged['_hr'] = merged['mean_heat_days'].rank(ascending=False)
        merged['_cr'] = merged['_pr'] + merged['_hr']
        top = merged.nsmallest(top_n, '_cr')
        for _, row in top.iterrows():
            ax.annotate(
                row['name'], (row['population'], row['mean_heat_days']),
                xytext=(5, 3), textcoords='offset points',
                fontsize=8, color='#c0392b',
            )

        xmed = merged['population'].median()
        ymed = merged['mean_heat_days'].median()
        ax.axvline(xmed, color='grey', linestyle=':', linewidth=1, alpha=0.6)
        ax.axhline(ymed, color='grey', linestyle=':', linewidth=1, alpha=0.6)

        xmin, xmax = merged['population'].min(), merged['population'].max()
        ymin, ymax = merged['mean_heat_days'].min(), merged['mean_heat_days'].max()
        xpad = (xmax - xmin) * 0.02
        ypad = (ymax - ymin) * 0.02

        quadrants = [
            (xmax - xpad, ymax - ypad, 'right', 'top',    'High pop\nHigh heat', '#c0392b', '#fdecea'),
            (xmin + xpad, ymax - ypad, 'left',  'top',    'Low pop\nHigh heat',  '#2980b9', '#eaf4fb'),
            (xmax - xpad, ymin + ypad, 'right', 'bottom', 'High pop\nLow heat',  '#e67e22', '#fef9e7'),
            (xmin + xpad, ymin + ypad, 'left',  'bottom', 'Low pop\nLow heat',   '#27ae60', '#eafaf1'),
        ]
        for x, y, ha, va, txt, fg, bg in quadrants:
            ax.text(x, y, txt, ha=ha, va=va, fontsize=8, color=fg,
                    bbox=dict(boxstyle='round,pad=0.2', fc=bg, alpha=0.8))

        ax.set_xlabel('Neighbourhood population', fontsize=10)
        ax.set_ylabel('Mean heat days', fontsize=10)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax.set_title(title, fontsize=10)
        ax.grid(True, alpha=0.2)

    suptitle = (f'Population vs heat-day exposure by neighbourhood \u2014 {city_name} {year}'
                if city_name else f'Population vs heat-day exposure {year}')
    fig.suptitle(suptitle, fontsize=13)
    plt.tight_layout()
    plt.show()


def plot_sensitivity_curves(
    curves: dict,
    ax: plt.Axes | None = None,
    highlight_thresholds: list | None = None,
) -> plt.Axes:
    """
    Overlay threshold sensitivity curves for multiple cities on one axes.

    Parameters
    ----------
    curves : dict mapping city label → DataFrame from threshold_sensitivity_curve().
             DataFrame must have columns 'threshold' and 'heat_days_per_year'.
    ax : existing axes to draw on; creates a new figure if None.
    highlight_thresholds : optional list of threshold values to mark with vertical lines.

    Returns
    -------
    The matplotlib Axes object.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5))

    for label, df in curves.items():
        ax.plot(df['threshold'], df['heat_days_per_year'],
                marker='o', markersize=4, linewidth=2, label=label)

    if highlight_thresholds:
        ymax = max(df['heat_days_per_year'].max() for df in curves.values())
        for thr in highlight_thresholds:
            ax.axvline(thr, color='grey', linestyle='--', linewidth=1, alpha=0.6)
            ax.text(thr + 0.15, ymax * 0.97, f'{thr}°C',
                    color='grey', fontsize=8, va='top')

    ax.set_xlabel('Threshold (°C)')
    ax.set_ylabel('Mean heat days per year')
    ax.set_title('Threshold sensitivity — daily Tmax')
    ax.legend()
    ax.grid(True, alpha=0.3)
    return ax


def plot_comparison_maps(
    da: xr.DataArray,
    gdf: gpd.GeoDataFrame,
    year: int,
    percentile: int,
    baseline: xr.DataArray,
    threshold: float = 30.0,
    city_name: str = '',
    vmax_abs: float | None = None,
    vmax_rel: float | None = None,
) -> tuple:
    """
    Side-by-side choropleth maps: absolute vs relative heat days per neighbourhood.

    Parameters
    ----------
    da : (time, lat, lon) Tmax DataArray.
    gdf : neighbourhood GeoDataFrame with 'name' and 'geometry'.
    year : calendar year to analyse.
    percentile : integer percentile label (must exist in baseline.percentile).
                 Used for the relative threshold and the panel title.
    baseline : per-pixel baseline DataArray (percentile, lat, lon) from load_baseline().
    threshold : absolute threshold in °C for the left panel.
    city_name : city label for the figure suptitle.
    vmax_abs : fixed colour-scale maximum for the absolute panel. If None, uses
               the per-city maximum (not comparable across cities).
    vmax_rel : fixed colour-scale maximum for the relative panel. Same caveat.

    Returns
    -------
    (abs_nbhd, rel_nbhd) — GeoDataFrames with 'mean_heat_days' column.
    """
    rel_thr  = baseline.sel(percentile=percentile)
    abs_map  = compute_absolute_heat_days(da, year, threshold)
    rel_map  = compute_relative_heat_days(da, year, rel_thr)
    abs_nbhd = aggregate_to_neighbourhoods(abs_map, gdf)
    rel_nbhd = aggregate_to_neighbourhoods(rel_map, gdf)

    import matplotlib.cm as mcm
    import matplotlib.patches as mpatches

    cmap_obj = mcm.get_cmap('YlOrRd')
    pct_temp = float(baseline.sel(percentile=percentile).mean())
    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    panels = [
        (abs_nbhd, axes[0], f'Absolute: Tmax >= {threshold:.0f} C  ({year})'),
        (rel_nbhd, axes[1], f'Relative: {percentile}th pct baseline ({pct_temp:.1f} °C)  ({year})'),
    ]
    for nbhd_gdf, ax, title in panels:
        series  = nbhd_gdf['mean_heat_days']
        working = nbhd_gdf.copy()

        # Percentile rank 0–1, ties broken by position so even identical values
        # (e.g. Teresina's 74 neighbourhoods at 356 days) spread across the
        # colour range rather than all collapsing to the same midpoint colour.
        working['_rank'] = series.rank(pct=True, method='first', na_option='keep')

        working.plot(
            column='_rank', ax=ax, cmap='YlOrRd',
            vmin=0, vmax=1,
            edgecolor='black', linewidth=0.4,
            legend=False,
            missing_kwds={'color': 'lightgrey', 'edgecolor': 'black', 'linewidth': 0.4},
        )

        # Legend: slice the rank-ordered data into 5 equal groups so there are
        # always 5 entries even when values cluster (e.g. 74 Teresina hoods at 356).
        valid_idx     = working['_rank'].dropna().index
        ranked_series = series.loc[valid_idx].sort_values()
        n_valid       = len(ranked_series)
        handles       = []
        for i in range(5):
            lo_i = int(i * n_valid / 5)
            hi_i = int((i + 1) * n_valid / 5)
            band = ranked_series.iloc[lo_i:hi_i]
            lo_v, hi_v = band.min(), band.max()
            handles.append(mpatches.Patch(
                facecolor=cmap_obj((i * 2 + 1) / 10),
                label=f'{lo_v:.1f}–{hi_v:.1f} days',
            ))
        n_nan = series.isna().sum()
        if n_nan:
            handles.append(mpatches.Patch(facecolor='lightgrey', label=f'No data ({n_nan})'))
        ax.legend(handles=handles, title='Mean heat days\n(quintile rank)',
                  fontsize=7, title_fontsize=7, loc='lower left')
        for _, row in nbhd_gdf.iterrows():
            cx, cy = row.geometry.centroid.x, row.geometry.centroid.y
            ax.annotate(
                row['name'], xy=(cx, cy), ha='center', va='center',
                fontsize=6.5, color='black',
                bbox=dict(boxstyle='round,pad=0.1', fc='white', alpha=0.5, lw=0),
            )
        ax.set_title(title, fontsize=10)
        ax.set_aspect('equal')

    suptitle = (f'Neighbourhood heat exposure — {city_name} {year}'
                if city_name else f'Heat exposure {year}')
    fig.suptitle(suptitle, fontsize=13)
    plt.tight_layout()
    plt.show()
    return abs_nbhd, rel_nbhd


def plot_quadrant(
    abs_nbhd: gpd.GeoDataFrame,
    rel_nbhd: gpd.GeoDataFrame,
    year: int,
    percentile: int,
    city_name: str = '',
) -> None:
    """
    Neighbourhood rank quadrant scatter: absolute vs relative heat-day rank.

    Rank 1 = most heat days. Axes are inverted so the highest-burden
    neighbourhoods appear at top-right. Spearman rho is printed below the plot.

    Parameters
    ----------
    abs_nbhd : GeoDataFrame with 'name' and 'mean_heat_days' — absolute counts.
    rel_nbhd : GeoDataFrame with 'name' and 'mean_heat_days' — relative counts.
    year : calendar year (for the title).
    percentile : relative-threshold percentile used (for the y-axis label).
    city_name : city label for the title.
    """
    merged = (
        abs_nbhd[['name', 'mean_heat_days']]
        .copy()
        .rename(columns={'mean_heat_days': 'abs_days'})
    )
    merged['rel_days'] = rel_nbhd['mean_heat_days'].values
    merged = merged.dropna(subset=['abs_days', 'rel_days']).reset_index(drop=True)

    n = len(merged)
    if n < 2:
        print('Too few neighbourhoods with data to plot.')
        return

    merged['abs_rank'] = merged['abs_days'].rank(ascending=False, method='min').astype(int)
    merged['rel_rank'] = merged['rel_days'].rank(ascending=False, method='min').astype(int)
    rho, pval = spearmanr(merged['abs_rank'], merged['rel_rank'])
    med = (n + 1) / 2

    fig, ax = plt.subplots(figsize=(9, 9))
    ax.scatter(merged['abs_rank'], merged['rel_rank'],
               s=80, color='steelblue', zorder=3, alpha=0.85)
    for _, row in merged.iterrows():
        ax.annotate(
            row['name'], (row['abs_rank'], row['rel_rank']),
            xytext=(5, 3), textcoords='offset points',
            fontsize=8, color='#222222',
        )

    ax.plot([1, n], [1, n], 'k--', linewidth=1, alpha=0.4)
    ax.axvline(med, color='grey', linestyle=':', linewidth=1, alpha=0.7)
    ax.axhline(med, color='grey', linestyle=':', linewidth=1, alpha=0.7)
    ax.invert_xaxis()
    ax.invert_yaxis()

    pad = n * 0.04
    quadrant_labels = [
        (1 + pad, 1 + pad, 'left',  'top',    'Robust priorities', '#c0392b', '#fdecea'),
        (n - pad, 1 + pad, 'right', 'top',    'Chronic burden',    '#e67e22', '#fef9e7'),
        (1 + pad, n - pad, 'left',  'bottom', 'Emerging concern',  '#2980b9', '#eaf4fb'),
        (n - pad, n - pad, 'right', 'bottom', 'Lower priority',    '#27ae60', '#eafaf1'),
    ]
    for x, y, ha, va, txt, fg, bg in quadrant_labels:
        ax.text(x, y, txt, ha=ha, va=va, fontsize=9, color=fg,
                bbox=dict(boxstyle='round,pad=0.25', fc=bg, alpha=0.8))

    ax.set_xlabel('Rank — absolute threshold (1 = most heat days)', fontsize=11)
    ax.set_ylabel(f'Rank — {percentile}th pct relative threshold (1 = most)', fontsize=11)
    title = f'Neighbourhood heat-day ranks: absolute vs relative\n'
    title += f'{city_name + " " if city_name else ""}{year}  |  {n} neighbourhoods'
    ax.set_title(title, fontsize=12)
    ax.grid(True, alpha=0.2)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.tight_layout()
    plt.show()

    p_str = f'{pval:.3f}' if pval >= 0.001 else '<0.001'
    print(f'Spearman rho = {rho:.3f}  (p = {p_str},  n = {n})')
