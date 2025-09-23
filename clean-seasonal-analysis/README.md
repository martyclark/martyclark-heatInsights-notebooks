# Clean Seasonal Extreme Heat Analysis

This folder contains a **streamlined, production-ready implementation** of the seasonal extreme heat days analysis methodology.

## 🎯 Overview

This notebook implements the climatologically appropriate extreme heat day calculation using seasonal percentiles:

```
Surface_Heat_Day = 1 if LST_daily_max > max(LST_abs, LST_rel)
```

Where:
- **LST_abs**: Absolute threshold (35°C)
- **LST_rel**: 90th percentile of temperatures for calendar day ± 5 days over reference period

## 📁 Files

- `seasonal_heat_analysis_clean.ipynb` - Main analysis notebook
- `README.md` - This documentation

## 🚀 Quick Start

### Prerequisites
- Earth Engine authentication configured
- Python environment with required packages (xarray, pandas, matplotlib, earthengine-api)
- Access to Google Earth Engine project 'tl-cities'

### Running the Analysis

1. **Open the notebook**:
   ```bash
   jupyter notebook seasonal_heat_analysis_clean.ipynb
   ```

2. **Run all cells sequentially** - the notebook is designed to run linearly from top to bottom

3. **Results will be saved** to `../outputs/clean_seasonal_analysis/`

### Default Configuration
- **Analysis Year**: 2020
- **Reference Period**: 2003-2019
- **Study Area**: Salvador, Brazil region
- **Thresholds**: 35°C absolute, 90th percentile
- **Day Window**: ±5 days

## 🔧 Customization

To analyze a different region or time period, modify the `CONFIG` dictionary in cell 4:

```python
CONFIG = {
    'analysis_year': 2020,           # Year to analyze
    'reference_start': 2003,         # Reference period start
    'reference_end': 2019,           # Reference period end
    'absolute_threshold': 35.0,      # °C
    'percentile_threshold': 90.0,    # percentile
    'day_window': 5,                 # ± days for seasonal calculation
    'max_temp_filter': 50.0,         # °C - filter extreme outliers
    'roi_bounds': [-38.7, -13.1, -38.3, -12.8],  # [west, south, east, north]
    'scale': 1000                    # meters
}
```

## 📊 Outputs

The analysis generates:

1. **NetCDF file**: Spatial results with proper CRS metadata
   - `seasonal_heat_analysis_2020.nc`

2. **CSV summary**: Method comparison statistics
   - `method_comparison_2020.csv`

3. **Documentation**: Methodology report
   - `clean_seasonal_methodology_2020.txt`

4. **Visualizations**: Comparison maps and distributions

## 🔬 Scientific Improvements

### Data Quality Filtering
- **Temperature outliers removed**: Values >50°C filtered out
- **Addresses GSHTD data quality issues**: Prevents extreme outliers (up to 88°C) from contaminating analysis
- **Scientifically realistic ranges**: Ensures valid surface air temperatures

### Methodological Advantages
- **Seasonal context**: July heat vs January heat appropriately weighted
- **Climatological accuracy**: Follows meteorological best practices
- **Sensitive detection**: Can identify winter/spring heat anomalies
- **Day-specific baselines**: Each day compared to its historical context

## 🏗️ Architecture

### Clean Design Principles
1. **Linear workflow** - Run cells in order, no complex dependencies
2. **Single responsibility** - Each cell performs one clear task
3. **Minimal complexity** - No widgets, simple configuration
4. **Robust error handling** - Clear validation and error messages
5. **Comprehensive documentation** - Every step explained

### Processing Flow
```
Setup → Data Extraction → Seasonal Percentiles → Heat Days Analysis → Visualization → Export
```

## 🔍 Debugging

If you encounter issues:

1. **Check Earth Engine authentication**:
   ```bash
   earthengine authenticate
   ```

2. **Verify data availability** for your region and time period

3. **Check memory usage** - reduce ROI size or increase scale parameter if needed

4. **Review temperature ranges** in the output - should be realistic (15-45°C for most regions)

## 📈 Expected Results

For the default Salvador, Brazil analysis:
- **Seasonal method**: ~3-4 mean heat days per pixel
- **Annual method**: ~4-5 mean heat days per pixel  
- **Strong correlation** between methods (r > 0.99)
- **Realistic temperatures**: Max ~38°C, filtered outliers

## 🆚 Improvements Over Previous Implementation

1. ✅ **Clean structure** - No scattered function definitions
2. ✅ **Data quality filtering** - Removes temperature outliers
3. ✅ **Streamlined processing** - No complex widgets
4. ✅ **Better error handling** - Clear validation steps
5. ✅ **Focus on science** - Less UI complexity, more analysis
6. ✅ **Proper documentation** - Each step clearly explained
7. ✅ **Production ready** - Can be easily adapted for different regions

## 📧 Support

For questions or issues:
1. Check the methodology documentation in outputs
2. Review the analysis validation steps in the notebook
3. Verify Earth Engine data availability for your region/time period

## 📚 References

- **GSHTD Dataset**: Global Surface Heat Temperature Database
- **Methodology**: Seasonal percentile approach for extreme heat detection
- **CRS**: EPSG:4326 (WGS84) with proper CF-compliant metadata