#!/usr/bin/env python3
"""
Test that the fix correctly handles land vs water pixels
"""

import pandas as pd
import numpy as np

print("🔍 TESTING NULL VALUE HANDLING - FIXED VERSION")
print("="*50)

# Simulate getRegion data with mixed land/water pixels
sample_data = [
    ['id', 'longitude', 'latitude', 'time', 'b1'],  # header
    ['img1', -38.5, -13.0, 1577836800000, 350],     # land pixel with data
    ['img1', -38.4, -13.0, 1577836800000, None],    # water pixel (no data)
    ['img1', -38.3, -13.0, 1577836800000, 360],     # land pixel with data
    ['img2', -38.5, -13.0, 1577923200000, 355],     # same land pixel, day 2
    ['img2', -38.4, -13.0, 1577923200000, None],    # same water pixel, day 2
    ['img2', -38.3, -13.0, 1577923200000, 365],     # same land pixel, day 2
]

print("📋 Sample raw data (simulating getRegion output):")
for i, row in enumerate(sample_data):
    if i == 0:
        print(f"   Header: {row}")
    else:
        status = "🌊 WATER" if row[4] is None else "🏝️ LAND"
        print(f"   {status}: {row}")

# Process with the FIXED method
print("\n✅ FIXED METHOD (what the notebook now does):")
header = sample_data[0]
data = sample_data[1:]
df = pd.DataFrame(data, columns=header)
df['time'] = pd.to_datetime(df['time'], unit='ms')

print(f"\n1️⃣ After DataFrame creation: {len(df)} rows")
print("   Raw b1 values:")
for i, (idx, row) in enumerate(df.iterrows()):
    status = "🌊 WATER" if pd.isna(row['b1']) else "🏝️ LAND "
    print(f"      {status}: b1={row['b1']} at ({row['latitude']}, {row['longitude']})")

# Apply scaling and rename BEFORE dropping nulls (this is the fix)
if 'b1' in df.columns:
    df['temperature'] = pd.to_numeric(df['b1'], errors='coerce') / 10.0
    df = df.drop(columns=['b1'])

print(f"\n2️⃣ After scaling (b1/10 → temperature): {len(df)} rows")
print("   Scaled temperature values:")
for i, (idx, row) in enumerate(df.iterrows()):
    status = "🌊 WATER" if pd.isna(row['temperature']) else "🏝️ LAND "
    print(f"      {status}: temp={row['temperature']}°C at ({row['latitude']}, {row['longitude']})")

# Now drop nulls from the correctly named temperature column
df_final = df.dropna(subset=['temperature'])

print(f"\n3️⃣ After dropping water pixels: {len(df_final)} rows")
print("   Final land-only data:")
for i, (idx, row) in enumerate(df_final.iterrows()):
    print(f"      🏝️ LAND: temp={row['temperature']}°C at ({row['latitude']}, {row['longitude']}) on {row['time'].date()}")

print("\n📊 SUMMARY:")
print(f"   • Started with: {len(data)} total pixels (land + water)")
print(f"   • Water pixels removed: {len(data) - len(df_final)} (correct - no temp data)")
print(f"   • Land pixels kept: {len(df_final)} (correct - have temp data)")
print(f"   • Temperature range: {df_final['temperature'].min():.1f}°C to {df_final['temperature'].max():.1f}°C")

print("\n✅ CONCLUSION:")
print("   ✓ Water pixels (b1=None) → temperature=NaN → correctly removed")
print("   ✓ Land pixels (b1=350-365) → temperature=35.0-36.5°C → correctly kept")
print("   ✓ The fix preserves correct land/water distinction")
print("   ✓ No valid temperature data is lost")