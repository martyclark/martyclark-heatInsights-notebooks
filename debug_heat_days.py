#!/usr/bin/env python3
"""
Debug script to identify the heat days calculation issue
"""

import xarray as xr
import numpy as np
import pandas as pd

print("🔍 DEBUGGING HEAT DAYS CALCULATION")
print("="*50)

# Load the NetCDF file
ds = xr.open_dataset('outputs/climate_analysis_2020.nc')
print("📊 Loaded NetCDF file")

# Print actual values from the NetCDF
print("\n🌡️ NetCDF Temperature Values:")
if 'annual_max' in ds.data_vars:
    annual_max = ds.annual_max
    print(f"   Annual max range: {annual_max.min().values:.1f} to {annual_max.max().values:.1f}°C")
    
    # Find pixels with highest temperatures
    max_temp_pixel = annual_max.where(annual_max == annual_max.max(), drop=True)
    if max_temp_pixel.size > 0:
        lat_max = float(max_temp_pixel.latitude.values.flat[0])
        lon_max = float(max_temp_pixel.longitude.values.flat[0])
        max_temp_val = float(max_temp_pixel.values.flat[0])
        print(f"   Hottest pixel: {max_temp_val:.1f}°C at ({lat_max:.3f}, {lon_max:.3f})")

print("\n🎯 Threshold Analysis:")
if 'threshold_used' in ds.data_vars:
    threshold = ds.threshold_used
    print(f"   Threshold range: {threshold.min().values:.1f} to {threshold.max().values:.1f}°C")
    
    # Check threshold at the hottest pixel
    if 'annual_max' in ds.data_vars:
        threshold_at_max = threshold.sel(latitude=lat_max, longitude=lon_max, method='nearest')
        print(f"   Threshold at hottest pixel: {threshold_at_max.values:.1f}°C")
        print(f"   Max temp vs threshold: {max_temp_val:.1f}°C vs {threshold_at_max.values:.1f}°C")
        print(f"   Should have heat days? {max_temp_val > threshold_at_max.values}")

print("\n🔥 Heat Days Analysis:")
if 'heat_days' in ds.data_vars:
    heat_days = ds.heat_days
    print(f"   Heat days range: {heat_days.min().values} to {heat_days.max().values}")
    print(f"   Total heat days across all pixels: {heat_days.sum().values}")
    
    # Check heat days at the hottest pixel
    heat_days_at_max = heat_days.sel(latitude=lat_max, longitude=lon_max, method='nearest')
    print(f"   Heat days at hottest pixel: {heat_days_at_max.values}")

print("\n📈 Reference Percentile Analysis:")
if 'reference_percentile' in ds.data_vars:
    ref_pct = ds.reference_percentile
    print(f"   95th percentile range: {ref_pct.min().values:.1f} to {ref_pct.max().values:.1f}°C")
    
    # Check if there are any valid percentiles (non-zero)
    valid_percentiles = (ref_pct > 0).sum()
    print(f"   Pixels with valid (>0) percentiles: {valid_percentiles.values}")
    
    # Check percentile at hottest pixel
    pct_at_max = ref_pct.sel(latitude=lat_max, longitude=lon_max, method='nearest')
    print(f"   95th percentile at hottest pixel: {pct_at_max.values:.1f}°C")

print("\n🚨 DIAGNOSIS:")
print("If annual max > threshold but heat_days = 0, then the heat days calculation logic is broken!")
print("This suggests the issue is in the daily temperature comparison, not the annual max calculation.")

ds.close()