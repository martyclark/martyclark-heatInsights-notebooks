"""
utils/ehf.py — Excess Heat Factor (EHF) computation functions.

Reference
---------
Nairn, J. & Fawcett, R. (2013). Defining heatwaves: the Excess Heat Factor.
Bureau of Meteorology, CAWCR Technical Report No. 060, Australia.

Definition
----------
EHF = EHI_sig × max(1, EHI_accl)

    EHI_sig  = T3 − T95_3day
        T3         = trailing 3-day mean of temperature
        T95_3day   = 95th percentile of T3 over the reference period (per pixel)

    EHI_accl = T3 − T30
        T30        = 30-day mean of the 30 days immediately preceding the
                     current 3-day window (days i-3 to i-32)

EHI_sig  measures how extreme the current 3-day period is relative to local
         climatology.  A positive value means the period exceeds the local
         95th percentile of 3-day means.

EHI_accl measures how much hotter the current 3-day period is than what the
         body has recently been acclimatised to.  Values > 1 amplify EHF;
         values < 1 are clamped to 1 so they do not suppress a significant event.

A heatwave day is any day where EHF > 0 (equivalently, where EHI_sig > 0).
EHF magnitude accumulates the intensity of heat stress across an entire season
or year.

Notes
-----
- This implementation uses a single per-pixel T95_3day threshold (not
  calendar-day varying), which is appropriate for tropical cities with a
  weak seasonal cycle relative to inter-annual variability.
- Temperature input should be daily (Tmax or Tmin); the functions are
  agnostic to which is supplied.  For closest alignment with the original
  Nairn & Fawcett definition, pass daily mean temperature (Tmean).
- The first 34 days of any time series will be NaN in EHF due to the
  30-day lag window plus the 3-day mean window (3 + 30 + 1 = 34 days of
  warm-up).  This is negligible for 18-year records.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr


# ---------------------------------------------------------------------------
# Core computations
# ---------------------------------------------------------------------------

def compute_t95_3day(da: xr.DataArray) -> xr.DataArray:
    """
    95th percentile of the 3-day trailing mean temperature per pixel.

    This is the EHI_sig threshold: T3 values above this level are considered
    climatologically extreme.

    Parameters
    ----------
    da : DataArray (time, lat, lon) or (time, y, x).
         Full reference-period temperature record.

    Returns
    -------
    DataArray (lat, lon) or (y, x) with the per-pixel T95_3day threshold.
    Units inherit from `da`.
    """
    t3 = da.rolling(time=3, min_periods=3).mean()
    t95 = t3.quantile(0.95, dim='time').drop_vars('quantile', errors='ignore')
    t95.attrs['long_name'] = '95th percentile of 3-day trailing mean temperature'
    t95.attrs['units']     = da.attrs.get('units', 'degC')
    t95.attrs['source']    = 'EHF T95_3day threshold'
    return t95


def compute_ehf(da: xr.DataArray, t95_3day: xr.DataArray) -> xr.DataArray:
    """
    Compute the full EHF time series.

    Parameters
    ----------
    da       : DataArray (time, lat, lon) — daily temperature.
    t95_3day : DataArray (lat, lon)       — T95 of 3-day means, from
               compute_t95_3day() or load_ehf_t95().

    Returns
    -------
    DataArray (time, lat, lon) — EHF values.
    Positive values indicate heatwave days; negative or zero indicate none.
    Units are °C (same as input, squared in principle but reported as °C for
    practical use since EHI_accl is unitless when acting as a multiplier).
    """
    time_dim = 'time'

    # 3-day trailing mean
    t3 = da.rolling({time_dim: 3}, min_periods=3).mean()

    # 30-day mean lagged by 3 days (days i-3 to i-32)
    t30 = da.rolling({time_dim: 30}, min_periods=30).mean().shift({time_dim: 3})

    # Components
    ehi_sig  = t3 - t95_3day            # broadcasts (lat,lon) against (time,lat,lon)
    ehi_accl = t3 - t30

    # EHF: clamp EHI_accl at minimum of 1 so it never suppresses a significant event
    ehf = ehi_sig * ehi_accl.clip(min=1.0)
    ehf.attrs['long_name'] = 'Excess Heat Factor'
    ehf.attrs['units']     = da.attrs.get('units', 'degC')
    return ehf


def compute_ehf_components(
    da: xr.DataArray,
    t95_3day: xr.DataArray,
) -> dict[str, xr.DataArray]:
    """
    Compute and return all intermediate EHF components for diagnostics.

    Returns a dict with keys:
        't3'       — 3-day trailing mean
        't30'      — 30-day lagged mean (antecedent acclimatisation baseline)
        'ehi_sig'  — significance component
        'ehi_accl' — acclimatisation component
        'ehf'      — final EHF
    """
    time_dim = 'time'
    t3   = da.rolling({time_dim: 3},  min_periods=3).mean()
    t30  = da.rolling({time_dim: 30}, min_periods=30).mean().shift({time_dim: 3})
    ehi_sig  = t3 - t95_3day
    ehi_accl = t3 - t30
    ehf      = ehi_sig * ehi_accl.clip(min=1.0)
    return {
        't3':       t3,
        't30':      t30,
        'ehi_sig':  ehi_sig,
        'ehi_accl': ehi_accl,
        'ehf':      ehf,
    }


def compute_ehf_annual_stats(ehf: xr.DataArray) -> xr.Dataset:
    """
    Compute per-pixel annual EHF statistics.

    Parameters
    ----------
    ehf : DataArray (time, lat, lon) from compute_ehf().

    Returns
    -------
    Dataset with annual (time, lat, lon) variables:

        heatwave_days  — count of days where EHF > 0 per year
        ehf_magnitude  — annual sum of EHF on heatwave days (°C)
        ehf_intensity  — mean EHF per heatwave day (magnitude / count);
                         NaN where no heatwave days occurred
    """
    ehf_pos = ehf.clip(min=0)                          # zero out non-heatwave days

    heatwave_days = (ehf > 0).resample(time='YS').sum(dim='time').astype('float32')
    ehf_magnitude = ehf_pos.resample(time='YS').sum(dim='time').astype('float32')

    # Mean intensity: avoid division by zero
    ehf_intensity = xr.where(
        heatwave_days > 0,
        ehf_magnitude / heatwave_days,
        np.nan,
    )

    ds = xr.Dataset({
        'heatwave_days': heatwave_days,
        'ehf_magnitude': ehf_magnitude,
        'ehf_intensity': ehf_intensity,
    })
    ds['heatwave_days'].attrs = {
        'long_name': 'EHF heatwave days per year',
        'units':     'count',
    }
    ds['ehf_magnitude'].attrs = {
        'long_name': 'Annual sum of EHF on heatwave days',
        'units':     'degC',
    }
    ds['ehf_intensity'].attrs = {
        'long_name': 'Mean EHF per heatwave day',
        'units':     'degC',
    }
    return ds


# ---------------------------------------------------------------------------
# Caching helpers
# ---------------------------------------------------------------------------

def save_ehf_t95(
    t95: xr.DataArray,
    city: str,
    data_dir: str = 'data',
    suffix: str = 'tmax',
) -> None:
    """
    Save the per-pixel T95_3day threshold to a NetCDF cache.

    Parameters
    ----------
    t95      : DataArray (lat, lon) from compute_t95_3day().
    city     : city key, e.g. 'salvador'.
    data_dir : output directory.
    suffix   : 'tmax' or 'tmin' — identifies which temperature variable was used.
    """
    path = Path(data_dir) / f'{city}_ehf_t95_{suffix}.nc'
    t95.to_dataset(name='t95_3day').to_netcdf(path)
    print(f'Saved EHF T95 threshold: {path}')


def load_ehf_t95(
    city: str,
    data_dir: str = 'data',
    suffix: str = 'tmax',
) -> xr.DataArray:
    """
    Load a cached T95_3day threshold.

    Raises FileNotFoundError if the cache does not exist — run
    compute_t95_3day() and save_ehf_t95() first.
    """
    path = Path(data_dir) / f'{city}_ehf_t95_{suffix}.nc'
    if not path.exists():
        raise FileNotFoundError(
            f'EHF T95 threshold not found: {path}\n'
            f'Run compute_t95_3day() and save_ehf_t95() first.'
        )
    da = xr.open_dataset(path)['t95_3day'].load()
    print(f'{city} EHF T95 ({suffix}): range {float(da.min()):.1f}–{float(da.max()):.1f} °C')
    return da


def save_ehf_annual_stats(
    ds: xr.Dataset,
    city: str,
    data_dir: str = 'data',
    suffix: str = 'tmax',
) -> None:
    """Save annual EHF statistics Dataset to NetCDF."""
    path = Path(data_dir) / f'{city}_ehf_annual_{suffix}.nc'
    ds.to_netcdf(path)
    print(f'Saved EHF annual stats: {path}')


def load_ehf_annual_stats(
    city: str,
    data_dir: str = 'data',
    suffix: str = 'tmax',
) -> xr.Dataset:
    """Load cached annual EHF statistics Dataset."""
    path = Path(data_dir) / f'{city}_ehf_annual_{suffix}.nc'
    if not path.exists():
        raise FileNotFoundError(
            f'EHF annual stats not found: {path}\n'
            f'Run compute_ehf_annual_stats() and save_ehf_annual_stats() first.'
        )
    ds = xr.open_dataset(path, decode_timedelta=False).load()
    print(
        f'{city} EHF annual stats ({suffix}): '
        f'{int(ds.time.dt.year.min())}–{int(ds.time.dt.year.max())}'
    )
    return ds
