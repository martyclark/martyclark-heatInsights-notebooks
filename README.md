# Heat Insights Notebooks

A comprehensive collection of Jupyter notebooks for **urban heat analysis** using Google Earth Engine (GEE), xarray, and climate data. This project provides multiple approaches to analyzing extreme heat patterns, with a focus on **intra-urban heat island analysis** and **seasonal heat detection methodologies**.

## 🔥 What These Notebooks Do

This collection provides complete workflows for:

- **🌡️ Extreme Heat Detection**: Calculate heat days using multiple methodologies (absolute thresholds, percentiles, seasonal approaches)
- **🏙️ Urban Heat Islands**: High-resolution (1km) intra-urban temperature analysis 
- **📊 Climate Trend Analysis**: Multi-year temperature trends and climate statistics
- **🌍 Global Coverage**: Support for worldwide analysis using GSHTD temperature data
- **🎯 Interactive Analysis**: User-friendly interfaces for ROI selection, threshold configuration
- **📈 Advanced Visualization**: Comprehensive mapping, time series, and statistical plots
- **📁 Spatial Export**: NetCDF and GeoTIFF export with proper CRS for GIS workflows

---

## 📓 Key Notebooks

### **Notebook 17: Complete xarray Climate Analysis** 
**`notebooks/17_xarray_climate_analysis.ipynb`**

**Purpose**: The most comprehensive and user-friendly approach to climate analysis

**Features**:
- **🎯 Triple ROI Selection**: Draw on map, enter coordinates, or browse for raster files
- **📊 Inline Visualization**: All plots appear directly in notebook cells
- **⚡ Efficient Processing**: Temporal chunking handles large datasets
- **🔍 Data Exploration**: Examine datasets before analysis with built-in diagnostics
- **📁 Complete Export**: CSV summaries, NetCDF spatial data, with proper WGS84 CRS
- **🛠️ File Browser**: Easy raster file selection without typing paths

**Best for**: Users who want a complete, reliable workflow with comprehensive visualization and export capabilities.

### **Notebook 18: Server-Side GEE Processing**
**`notebooks/18_gee_server_side_xarray.ipynb`** 

**Purpose**: Ultra-efficient approach using GEE's computational power

**Features**:
- **⚡ Lightning Fast**: All heavy computation done on Google's servers
- **🚀 No Data Limits**: Bypasses client-side memory constraints  
- **🔄 Direct Array Extraction**: No file exports, just raw pixel data extraction
- **💾 Minimal Bandwidth**: Only download final processed results
- **📊 Full 1km Resolution**: No compromise on spatial detail
- **🎯 Perfect for Large ROIs**: Handles city-scale analysis efficiently

**Best for**: Large-scale urban analysis where speed and efficiency are critical, or when dealing with very large geographic areas.

### **Notebook 19: Seasonal Extreme Heat Analysis** 
**`notebooks/19_seasonal_extreme_heat_analysis.ipynb`**

**Purpose**: **Climatologically appropriate** extreme heat detection using seasonal percentiles

**Features**:
- **🔬 Scientific Method**: Each day compared to historical temperatures for same calendar day ± window
- **📅 Seasonal Context**: July heat vs January heat appropriately weighted
- **🎯 Enhanced Detection**: Can identify winter/spring heat anomalies
- **📊 Method Comparison**: Side-by-side analysis of seasonal vs annual approaches
- **📈 Time Series Analysis**: Full 2003-2020 trend analysis and temperature anomalies
- **📋 Methodology Documentation**: Complete scientific documentation of approach

**Formula**: `Heat_Day = LST_max > max(absolute_threshold, seasonal_percentile)`

**Best for**: Researchers who need climatologically sound extreme heat detection that accounts for natural seasonal temperature cycles.

---

## 🏗️ Setup

1. **Create Python environment:**
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up GEE authentication** (follow prompts)

4. **Start Jupyter:**
```bash
jupyter lab
```

## 📁 Project Structure

- **`notebooks/`** - Analysis notebooks (19 total, see key notebooks above)
- **`clean-seasonal-analysis/`** - Clean presentation-ready seasonal analysis notebooks
- **`src/`** - Reusable Python modules for GEE utilities
- **`data/`** - Input datasets and vulnerability analysis results  
- **`outputs/`** - Generated maps, NetCDF files, and analysis results
- **`config/`** - Configuration files for different analysis regions

## 🌍 Global Coverage

Supports analysis worldwide using the **Global Surface Heat Temperature Database (GSHTD)**:
- **North America** (including Mexico)
- **Latin America** (South America + Caribbean)
- **Europe & Asia**
- **Africa**
- **Australia & Oceania**

## 🎯 Analysis Capabilities

### Heat Metrics Calculated:
- **Extreme Heat Days**: Days exceeding temperature thresholds
- **Temperature Trends**: Multi-year warming/cooling trends
- **Annual Extremes**: Maximum, minimum, mean, and range
- **Seasonal Means**: Temperature patterns by season
- **Heat Wave Detection**: Multi-day extreme heat events
- **Urban Heat Islands**: Intra-city temperature variations

### Threshold Methods:
- **Absolute**: Fixed temperature thresholds (e.g., 35°C)
- **Percentile**: Historical percentile-based (e.g., 90th percentile)
- **Seasonal**: Day-of-year specific percentiles (climatologically appropriate)
- **Combined**: Maximum of absolute and percentile thresholds

---

## 🚀 Getting Started

1. **For comprehensive analysis**: Start with **Notebook 17**
2. **For large-scale efficiency**: Use **Notebook 18** 
3. **For climatological research**: Try **Notebook 19**

Each notebook includes:
- ✅ Interactive ROI selection
- ✅ Configurable parameters
- ✅ Built-in visualization
- ✅ Spatial data export
- ✅ Comprehensive documentation

All notebooks produce **GIS-ready outputs** with proper coordinate reference systems for integration into broader spatial analysis workflows.