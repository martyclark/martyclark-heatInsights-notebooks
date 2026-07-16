"""
Pixel-level vs neighbourhood-level CV comparison for heat days and population.

Answers whether neighbourhood aggregation in build_nbhd_table smooths out genuine
spatial variation in the temperature signal, by comparing:
  - CV computed over raw pixels within each city boundary
  - CV computed over neighbourhood-aggregated values (as in notebook 07)

Run from heat_threshold_analysis/ directory.
"""
import sys, os
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from shapely.ops import unary_union

sys.path.insert(0, os.path.abspath('.'))
from utils.heat import (
    CITIES, load_city, load_tx90p_threshold, load_neighbourhood_boundaries,
    compute_absolute_heat_days,
    aggregate_to_neighbourhoods, aggregate_person_days_to_neighbourhoods,
    _point_in_poly_mask,
)

DATA_DIR      = 'data'
DIAG_YEAR     = 2020
ABS_THRESHOLD = 30.0
PERCENTILE    = 90
CITY_KEYS     = ['salvador', 'teresina', 'caceres']


def load_pop_grid(city: str, year: int) -> xr.DataArray:
    path = f'{DATA_DIR}/{city}_pop_1km_{year}.nc'
    return xr.open_dataset(path)['population']


def count_doy_exceedances(da: xr.DataArray, thresh_doy: xr.DataArray) -> xr.DataArray:
    aligned = thresh_doy.sel(dayofyear=da.time.dt.dayofyear)
    return (da > aligned).resample(time='YS').sum(dim='time')


def pixel_cv(values: np.ndarray) -> float:
    """CV for a 1-D array of valid (non-NaN, positive) values."""
    m = np.nanmean(values)
    if m == 0:
        return np.nan
    return float(np.nanstd(values) / m)


def pixels_within_city(city_boundary, lons: np.ndarray, lats: np.ndarray) -> np.ndarray:
    """Boolean 1-D mask for pixel centroids inside city_boundary polygon."""
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    return _point_in_poly_mask(city_boundary, lon_grid.ravel(), lat_grid.ravel())


def compute_pixel_cvs(city_key: str) -> dict:
    print(f'\n--- {CITIES[city_key]["label"]} ---')

    da         = load_city(city_key, DATA_DIR)
    da.attrs.setdefault('units', 'degC')
    thresh     = load_tx90p_threshold(city_key, DATA_DIR)
    gdf        = load_neighbourhood_boundaries(city_key, DATA_DIR)
    pop_grid   = load_pop_grid(city_key, DIAG_YEAR)

    # --- heat-day grids at pixel resolution ---
    abs_hd = compute_absolute_heat_days(da, DIAG_YEAR, ABS_THRESHOLD)

    thresh_90 = thresh.sel(percentile=PERCENTILE)
    tx_annual = count_doy_exceedances(da, thresh_90)
    tx_hd = (
        tx_annual
        .isel(time=(tx_annual.time.dt.year == DIAG_YEAR))
        .squeeze('time')
    )

    # --- city boundary = union of all neighbourhood polygons ---
    city_boundary = unary_union(gdf.geometry.values)

    # --- flatten to 1-D arrays ---
    lats = abs_hd.lat.values
    lons = abs_hd.lon.values
    city_mask = pixels_within_city(city_boundary, lons, lats)

    abs_vals = abs_hd.values.ravel()
    tx_vals  = tx_hd.values.ravel()
    pop_vals = pop_grid.interp(lat=abs_hd.lat, lon=abs_hd.lon, method='nearest').values.ravel()

    # Filter: inside city AND populated
    pop_mask  = np.isfinite(pop_vals) & (pop_vals > 0)
    heat_mask = np.isfinite(abs_vals) & np.isfinite(tx_vals)
    valid     = city_mask & pop_mask & heat_mask

    print(f'  Valid pixels (city + populated): {valid.sum():,}')
    print(f'  Population   range: {pop_vals[valid].min():.0f}–{pop_vals[valid].max():.0f}')
    print(f'  Abs heat days range: {abs_vals[valid].min():.0f}–{abs_vals[valid].max():.0f}')
    print(f'  TX90p hd range:      {tx_vals[valid].min():.0f}–{tx_vals[valid].max():.0f}')

    return {
        'pixel_cv_population': pixel_cv(pop_vals[valid]),
        'pixel_cv_abs_hd':     pixel_cv(abs_vals[valid]),
        'pixel_cv_tx90p_hd':   pixel_cv(tx_vals[valid]),
        'n_pixels':            int(valid.sum()),
    }


def compute_nbhd_cvs(city_key: str) -> dict:
    da       = load_city(city_key, DATA_DIR)
    da.attrs.setdefault('units', 'degC')
    thresh   = load_tx90p_threshold(city_key, DATA_DIR)
    gdf      = load_neighbourhood_boundaries(city_key, DATA_DIR)
    pop_grid = load_pop_grid(city_key, DIAG_YEAR)

    abs_hd = compute_absolute_heat_days(da, DIAG_YEAR, ABS_THRESHOLD)

    thresh_90 = thresh.sel(percentile=PERCENTILE)
    tx_annual = count_doy_exceedances(da, thresh_90)
    tx_hd = (
        tx_annual
        .isel(time=(tx_annual.time.dt.year == DIAG_YEAR))
        .squeeze('time')
    )

    pop_nbhd    = aggregate_person_days_to_neighbourhoods(pop_grid, gdf, col='population')
    abs_hd_nbhd = aggregate_to_neighbourhoods(abs_hd, gdf, col='abs_hd')
    tx_hd_nbhd  = aggregate_to_neighbourhoods(tx_hd,  gdf, col='tx90p_hd')

    df = gdf[['name']].copy()
    df['population'] = pop_nbhd['population'].values
    df['abs_hd']     = abs_hd_nbhd['abs_hd'].values
    df['tx90p_hd']   = tx_hd_nbhd['tx90p_hd'].values
    df = df.dropna().reset_index(drop=True)

    def cv(series):
        m = series.mean()
        return series.std() / m if m > 0 else np.nan

    return {
        'nbhd_cv_population': cv(df['population']),
        'nbhd_cv_abs_hd':     cv(df['abs_hd']),
        'nbhd_cv_tx90p_hd':   cv(df['tx90p_hd']),
        'n_nbhds':            len(df),
    }


def main():
    rows = []
    for city_key in CITY_KEYS:
        print(f'\n{"="*60}')
        print(f'Processing: {CITIES[city_key]["label"]}')

        pixel = compute_pixel_cvs(city_key)
        nbhd  = compute_nbhd_cvs(city_key)

        for var, p_key, n_key in [
            ('population', 'pixel_cv_population', 'nbhd_cv_population'),
            ('abs_hd',     'pixel_cv_abs_hd',     'nbhd_cv_abs_hd'),
            ('tx90p_hd',   'pixel_cv_tx90p_hd',   'nbhd_cv_tx90p_hd'),
        ]:
            rows.append({
                'City':            CITIES[city_key]['label'],
                'Variable':        var,
                'N pixels':        pixel['n_pixels'],
                'N nbhds':         nbhd['n_nbhds'],
                'Pixel-level CV':  pixel[p_key],
                'Nbhd-level CV':   nbhd[n_key],
                'Ratio (px/nbhd)': pixel[p_key] / nbhd[n_key] if nbhd[n_key] and nbhd[n_key] > 0 else np.nan,
            })

    df = pd.DataFrame(rows)

    print('\n\n' + '='*80)
    print('RESULT: Pixel-level vs Neighbourhood-level CV Comparison')
    print('='*80)
    print(df.to_string(index=False, float_format='{:.3f}'.format))

    print('\n\nINTERPRETATION:')
    print('  Ratio > 1: aggregation smooths spatial variation (pixel CV > nbhd CV)')
    print('  Ratio ≈ 1: aggregation preserves spatial variation')
    print('  A substantially higher pixel-level heat-day CV vs nbhd-level')
    print('  suggests genuine sub-neighbourhood temperature variation is being lost.')

    # Highlight heat-day variables
    heat_rows = df[df['Variable'].isin(['abs_hd', 'tx90p_hd'])]
    print('\nHeat-day rows only (key diagnostic):')
    print(heat_rows[['City', 'Variable', 'Pixel-level CV', 'Nbhd-level CV', 'Ratio (px/nbhd)']].to_string(
        index=False, float_format='{:.3f}'.format))


if __name__ == '__main__':
    main()
