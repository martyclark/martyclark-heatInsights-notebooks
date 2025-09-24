# Heat Insights Setup Instructions

This project implements a simple methodology for extreme heat analysis using Google Earth Engine and Jupyter notebooks.

## Quick Setup

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

Or run the automated setup script:

```bash
python setup_environment.py
```

### 2. Google Earth Engine Setup

#### Option A: If you already have GEE access
```bash
# Authenticate with Google Earth Engine
earthengine authenticate

# Set your default project (replace with your project ID)
earthengine set_project YOUR_PROJECT_ID
```

#### Option B: If you need GEE access
1. Visit [Google Earth Engine Signup](https://earthengine.google.com/signup/)
2. Sign up for Google Earth Engine access
3. Once approved, run the authentication commands above

### 3. Verify Setup

Run the first cell of `09_phase1_era5_data_setup.ipynb` to verify your environment:
- ✅ All packages installed
- ✅ Google Earth Engine authenticated

## Alternative: Demo Mode

If you don't have Google Earth Engine access, the notebooks will run in **demo mode** using synthetic data to demonstrate the EHF methodology.

## Required Packages

### Core Dependencies
- `earthengine-api>=0.1.380` - Google Earth Engine Python API
- `geemap>=0.32.0` - Interactive mapping with GEE
- `pandas>=2.0.0` - Data manipulation
- `numpy>=1.24.0` - Numerical computing
- `matplotlib>=3.7.0` - Plotting
- `seaborn>=0.12.0` - Statistical visualization

### Climate Analysis
- `climdx-kit==1.0.1` - Climate indices calculation
- `xarray>=2023.6.0` - Multi-dimensional data
- `netCDF4>=1.6.0` - NetCDF file support
- `scipy>=1.11.0` - Scientific computing

### Jupyter Environment
- `jupyter>=1.0.0` - Jupyter notebook server
- `jupyterlab>=4.0.0` - JupyterLab interface
- `ipywidgets>=8.0.0` - Interactive widgets

## Project Structure

```
heatInsights-notebooks/
├── notebooks/
│   ├── 09_phase1_era5_data_setup.ipynb      # Data setup & preprocessing
│   ├── 10_phase2_ehf_baseline.ipynb         # Baseline & thresholds
│   ├── 11_phase3_ehf_implementation.ipynb   # Core EHF calculation
│   ├── 12_phase4_heat_wave_metrics.ipynb    # Annual metrics (HWF, HWN, etc.)
│   └── 13_phase5_validation_outputs.ipynb   # Validation & final outputs
├── data/
│   ├── baseline/           # EHF baseline data
│   ├── ehf_results/        # Daily EHF and events
│   └── heat_wave_metrics/  # Annual metrics
├── outputs/
│   ├── baseline_analysis/  # Analysis visualizations
│   └── final_report/       # Final reports
├── requirements.txt        # Python dependencies
├── environment.yml         # Conda environment
└── setup_environment.py   # Automated setup script
```

## Usage

### 1. Start with Phase 1
Open and run `09_phase1_era5_data_setup.ipynb` to:
- Extract ERA5-Land temperature data
- Set up city-based analysis
- Prepare temperature time series

### 2. Continue through all phases
Run notebooks in sequence (09 → 10 → 11 → 12 → 13) for complete EHF analysis.

### 3. Key Outputs
- **Daily EHF time series**: Complete heat wave detection
- **Event catalogs**: Heat wave events with duration, intensity
- **Annual metrics**: HWF, HWN, HWD, HWA, HWM
- **Comparative analysis**: Multi-city heat wave patterns

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'geemap'"
```bash
pip install geemap
```

#### "EEException: Not signed up for Earth Engine"
1. Visit https://earthengine.google.com/signup/
2. Sign up for Google Earth Engine
3. Run `earthengine authenticate`

#### "No module named 'climdx_kit'"
```bash
pip install climdx-kit==1.0.1
```

### Environment Issues

#### Use virtual environment (recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Use conda environment
```bash
conda env create -f environment.yml
conda activate heatinsights
```

## Support

If you encounter issues:

1. Check that all packages are installed: `pip list`
2. Verify GEE authentication: `earthengine authenticate`
3. Run setup script: `python setup_environment.py`
4. Try demo mode if GEE access is unavailable

## Data Sources

- **ERA5-Land**: ECMWF Reanalysis hourly temperature data
- **GHS Urban Database**: Global Human Settlement urban areas
- **Methodology**: Perkins & Alexander (2013) EHF implementation

The notebooks provide a complete, reproducible workflow for global urban heat wave assessment using the EHF methodology.
