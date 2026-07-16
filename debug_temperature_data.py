#!/usr/bin/env python3
"""
Debug the temperature data extraction issue
"""

import ee
import pandas as pd
import numpy as np

print("🔍 DEBUGGING TEMPERATURE DATA EXTRACTION")
print("="*50)

# Initialize EE
try:
    ee.Initialize(project='tl-cities')
    print("✅ Earth Engine initialized")
except Exception as e:
    print(f"❌ EE init failed: {e}")
    exit(1)

# Test coordinates around Salvador, Brazil (should have data)
test_geom = ee.Geometry.Rectangle([-38.6, -13.1, -38.4, -12.9])

print(f"\n🎯 Testing data extraction for Salvador region...")
print(f"   Bounds: {test_geom.bounds().getInfo()}")

# Test GSHTD collection
collection_id = "projects/sat-io/open-datasets/global-daily-air-temp/latin_america"
print(f"   Collection: {collection_id}")

# Get a small sample for 2020
test_collection = (ee.ImageCollection(collection_id)
                   .filterDate('2020-01-01', '2020-01-05')
                   .filterBounds(test_geom)
                   .filter(ee.Filter.eq('prop_type', 'tmax')))

collection_size = test_collection.size().getInfo()
print(f"   Collection size (4 days): {collection_size}")

if collection_size == 0:
    print("❌ No images found - this is the root problem!")
    
    # Check if any data exists in the region
    all_collection = ee.ImageCollection(collection_id).filterBounds(test_geom)
    all_size = all_collection.size().getInfo()
    print(f"   Total images in region (any date): {all_size}")
    
    if all_size == 0:
        print("❌ No GSHTD data coverage for this region!")
    else:
        # Check what prop_types exist
        prop_types = all_collection.aggregate_array('prop_type').distinct().getInfo()
        print(f"   Available prop_types: {prop_types}")
        
        # Check date range
        dates = all_collection.aggregate_array('system:time_start').getInfo()
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            print(f"   Date range: {pd.to_datetime(min_date, unit='ms')} to {pd.to_datetime(max_date, unit='ms')}")
else:
    print("✅ Found images - testing extraction...")
    
    # Test extraction
    first_image = test_collection.first()
    
    # Check if image has data
    pixel_count = first_image.select('b1').reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=test_geom,
        scale=1000,
        maxPixels=1e6
    ).getInfo()
    
    print(f"   Pixels in first image: {pixel_count}")
    
    # Get sample values
    sample_data = first_image.select('b1').sample(
        region=test_geom,
        scale=1000,
        numPixels=5
    ).getInfo()
    
    print(f"   Sample raw values: {[f['properties']['b1'] for f in sample_data['features']]}")
    
    # Test scaling (divide by 10)
    scaled_image = first_image.select('b1').divide(10)
    sample_scaled = scaled_image.sample(
        region=test_geom,
        scale=1000,
        numPixels=5
    ).getInfo()
    
    print(f"   Sample scaled values: {[f['properties']['b1'] for f in sample_scaled['features']]}")
    
    # Test getRegion
    try:
        region_data = test_collection.getRegion(
            geometry=test_geom,
            scale=1000,
            crs='EPSG:4326'
        ).getInfo()
        
        print(f"   getRegion returned {len(region_data)} rows")
        if len(region_data) > 1:
            header = region_data[0]
            sample_row = region_data[1]
            print(f"   Headers: {header}")
            print(f"   Sample row: {sample_row}")
            
            # Check temperature values
            if 'b1' in header:
                temp_idx = header.index('b1')
                temps = [row[temp_idx] for row in region_data[1:] if row[temp_idx] is not None]
                if temps:
                    print(f"   Raw temperature range: {min(temps)} to {max(temps)}")
                    scaled_temps = [t/10 for t in temps]
                    print(f"   Scaled temperature range: {min(scaled_temps):.1f} to {max(scaled_temps):.1f}°C")
                else:
                    print("   ❌ No valid temperature values!")
    except Exception as e:
        print(f"   ❌ getRegion failed: {e}")

print("\n🚨 DIAGNOSIS:")
print("If no images found or no pixels, then the data extraction is failing at the source.")
print("If images found but values are null/zero, then the scaling or processing is wrong.")