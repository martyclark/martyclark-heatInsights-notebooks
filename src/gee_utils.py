"""
Google Earth Engine utility functions for heat analysis
"""

import ee
import pandas as pd
from typing import Dict, List, Optional, Tuple


def initialize_gee(service_account_path: Optional[str] = None) -> None:
    """
    Initialize Google Earth Engine
    
    Args:
        service_account_path: Path to service account JSON file (optional)
    """
    try:
        if service_account_path:
            credentials = ee.ServiceAccountCredentials(None, service_account_path)
            ee.Initialize(credentials)
        else:
            ee.Initialize()
        print("✓ Google Earth Engine initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize GEE: {e}")
        raise


def get_temperature_data(
    geometry: ee.Geometry,
    start_date: str,
    end_date: str,
    collection: str = "MODIS/061/MOD11A1"
) -> ee.ImageCollection:
    """
    Get temperature data from GEE
    
    Args:
        geometry: Area of interest
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        collection: GEE collection ID
        
    Returns:
        Filtered image collection
    """
    return (ee.ImageCollection(collection)
            .filterBounds(geometry)
            .filterDate(start_date, end_date)
            .select(['LST_Day_1km', 'LST_Night_1km']))


def kelvin_to_celsius(image: ee.Image) -> ee.Image:
    """Convert Kelvin to Celsius and scale MODIS LST data"""
    return (image.multiply(0.02)
            .subtract(273.15)
            .copyProperties(image, ['system:time_start']))


def compute_heat_statistics(
    image_collection: ee.ImageCollection,
    geometry: ee.Geometry,
    scale: int = 1000
) -> Dict:
    """
    Compute heat statistics for a region
    
    Args:
        image_collection: Temperature image collection
        geometry: Area of interest
        scale: Resolution in meters
        
    Returns:
        Dictionary with statistics
    """
    
    def compute_stats(image):
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.max(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.min(),
                sharedInputs=True
            ),
            geometry=geometry,
            scale=scale,
            maxPixels=1e9
        )
        return ee.Feature(None, stats).set('date', image.date().format('YYYY-MM-dd'))
    
    stats_collection = image_collection.map(compute_stats)
    return stats_collection.getInfo()


def export_to_drive(
    image: ee.Image,
    description: str,
    folder: str = "GEE_Exports",
    scale: int = 1000,
    region: ee.Geometry = None
) -> None:
    """
    Export image to Google Drive
    
    Args:
        image: Image to export
        description: Export description
        folder: Drive folder name
        scale: Resolution in meters
        region: Export region
    """
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=folder,
        scale=scale,
        region=region,
        maxPixels=1e9
    )
    task.start()
    print(f"✓ Export task '{description}' started")