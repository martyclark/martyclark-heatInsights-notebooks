#!/usr/bin/env python3
"""
Debug the heat days calculation specifically
"""

import xarray as xr
import numpy as np

print("🔍 DEBUGGING HEAT DAYS CALCULATION")
print("="*50)

# Load the NetCDF file
ds = xr.open_dataset('outputs/climate_analysis_2020.nc')

print("📊 Current NetCDF shows:")
print(f"   Annual max: {ds.annual_max.min().values:.1f} to {ds.annual_max.max().values:.1f}°C")
print(f"   Threshold used: {ds.threshold_used.min().values:.1f} to {ds.threshold_used.max().values:.1f}°C")  
print(f"   Heat days: {ds.heat_days.min().values} to {ds.heat_days.max().values}")

# Find the hottest pixel
hottest_pixel = ds.where(ds.annual_max == ds.annual_max.max(), drop=True)
if hottest_pixel.annual_max.size > 0:
    lat_hot = float(hottest_pixel.latitude.values.flat[0])
    lon_hot = float(hottest_pixel.longitude.values.flat[0])
    annual_max_hot = float(hottest_pixel.annual_max.values.flat[0])
    threshold_hot = float(hottest_pixel.threshold_used.values.flat[0])
    heat_days_hot = float(hottest_pixel.heat_days.values.flat[0])
    
    print(f"\n🔥 Hottest pixel analysis:")
    print(f"   Location: ({lat_hot:.3f}, {lon_hot:.3f})")
    print(f"   Annual max: {annual_max_hot:.1f}°C")
    print(f"   Threshold: {threshold_hot:.1f}°C")
    print(f"   Heat days: {heat_days_hot}")
    print(f"   Should have heat days? {annual_max_hot > threshold_hot}")

print(f"\n🚨 KEY INSIGHT:")
print(f"The heat days calculation looks at DAILY temperatures vs threshold")
print(f"But annual_max is the MAXIMUM temperature for the entire year")
print(f"If annual_max < threshold, then NO DAILY temperature exceeded threshold")
print(f"This suggests either:")
print(f"  1. The daily temperature data has different values than the annual_max suggests")
print(f"  2. There's a bug in the heat days calculation logic")
print(f"  3. The thresholds are calculated incorrectly")

# Let's check if there are pixels where annual_max > threshold
comparison = ds.annual_max > ds.threshold_used
pixels_should_have_heat_days = comparison.sum().values
print(f"\n🧮 Logic check:")
print(f"   Pixels where annual_max > threshold: {pixels_should_have_heat_days}")
print(f"   These pixels should have heat_days > 0")

if pixels_should_have_heat_days > 0:
    print(f"\n❌ BUG CONFIRMED: {pixels_should_have_heat_days} pixels should have heat days but all show 0")
    print(f"   This means the heat days calculation logic in cell-11 is broken!")
else:
    print(f"\n✅ Logic consistent: No pixels have annual_max > threshold")
    print(f"   Zero heat days is scientifically correct - no extreme temperatures in 2020")

ds.close()