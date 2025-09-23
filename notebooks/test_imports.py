#!/usr/bin/env python
# Test script to check package imports

import sys
print("Python executable:", sys.executable)
print("Python version:", sys.version)
print()

packages_to_test = [
    'xarray',
    'pandas', 
    'numpy',
    'matplotlib',
    'rasterio',
    'rioxarray'
]

for package in packages_to_test:
    try:
        module = __import__(package)
        version = getattr(module, '__version__', 'unknown')
        print(f"✅ {package}: {version}")
    except ImportError as e:
        print(f"❌ {package}: {e}")

print("\nIf rioxarray shows as missing above, try running:")
print("pip install --upgrade rioxarray")
print("or")
print("conda install -c conda-forge rioxarray")