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
    da = xr.open_dataset(path)['tmax']
    print(f'{name}: shape {dict(zip(da.dims, da.shape))}  '
          f'{str(da.time.values[0])[:10]} to {str(da.time.values[-1])[:10]}')
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
    da = xr.open_dataset(path)['tmax']
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
        means.append(float(valid.mean()) if len(valid) > 0 else np.nan)

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


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

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

    Returns
    -------
    (abs_nbhd, rel_nbhd) — GeoDataFrames with 'mean_heat_days' column.
    """
    rel_thr  = baseline.sel(percentile=percentile)
    abs_map  = compute_absolute_heat_days(da, year, threshold)
    rel_map  = compute_relative_heat_days(da, year, rel_thr)
    abs_nbhd = aggregate_to_neighbourhoods(abs_map, gdf)
    rel_nbhd = aggregate_to_neighbourhoods(rel_map, gdf)

    cmap = 'YlOrRd'
    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    panels = [
        (abs_nbhd, axes[0], f'Absolute: Tmax >= {threshold:.0f} C  ({year})'),
        (rel_nbhd, axes[1], f'Relative: {percentile}th pct baseline  ({year})'),
    ]
    for nbhd_gdf, ax, title in panels:
        vmax = max(float(nbhd_gdf['mean_heat_days'].max()), 1.0)
        nbhd_gdf.plot(
            column='mean_heat_days', ax=ax, cmap=cmap,
            vmin=0, vmax=vmax, edgecolor='black', linewidth=0.4,
            legend=True, legend_kwds={'shrink': 0.7, 'label': 'Mean heat days'},
        )
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
