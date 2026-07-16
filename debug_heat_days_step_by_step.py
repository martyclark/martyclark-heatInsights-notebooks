#!/usr/bin/env python3
"""
Debug the heat days calculation step by step
"""

import xarray as xr
import numpy as np

print("🔍 DEBUGGING HEAT DAYS CALCULATION STEP BY STEP")
print("="*60)

# We need to recreate the calculation to see where it breaks
# But first, let's check if we have access to the raw temperature data

# Check if there's a debug_df from the extraction
import pandas as pd
import os

print("🔍 Looking for raw temperature data...")

# Check if there are any pickle files or debug data
if os.path.exists('debug_df.pkl'):
    print("Found debug_df.pkl")
elif os.path.exists('temperature_data.pkl'):
    print("Found temperature_data.pkl")
else:
    print("No debug files found")

# Let's try to understand what the charts are showing vs calculation
print("\n📊 Understanding the discrepancy:")
print("Charts show temperatures 60-80°C but heat days = 0")
print("This suggests either:")
print("1. Wrong data being used for charts vs heat days calculation")
print("2. Bug in heat days calculation logic") 
print("3. Units mismatch (Kelvin vs Celsius)")
print("4. Time filtering removing all 2020 data")

print("\n🌡️ Temperature unit check:")
print("If raw data is in Kelvin:")
print("  - 60°C = 333K")
print("  - 80°C = 353K") 
print("  - But we divide by 10, so raw values would be 3330-3530")
print("  - Charts showing 60-80°C suggests units might already be Celsius")

print("\n🔍 Recommended debugging steps:")
print("1. Check what time range analysis_data actually contains")
print("2. Verify threshold shape matches temperature data shape") 
print("3. Test the boolean comparison manually")
print("4. Check if fillna(0) is overriding valid results")

print("\n💡 HYPOTHESIS:")
print("The charts are showing ALL years (2010-2020) but heat days")
print("calculation only looks at 2020 data. If 2020 was cooler,")
print("heat days could be zero even with hot days in other years.")

print("\nTo debug this properly, we need to:")
print("1. Re-run the notebook with print statements in the calculation")
print("2. Check the actual data shapes and values at each step")
print("3. Verify the time filtering is working correctly")