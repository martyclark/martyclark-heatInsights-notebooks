# Heat Threshold Analysis

Three-city comparison of absolute vs relative heat day thresholds using the
Zhang et al. (2022) 1 km daily maximum near-surface air temperature dataset.

**Cities:** Salvador · Teresina · Cáceres (all Brazil)

---

## Pipeline

Run the notebooks **in order**:

| Step | Notebook | Description | Frequency |
|------|----------|-------------|-----------|
| 1 | `01_data_acquisition.ipynb` | Download Tmax from GEE → `data/*.nc` | Once (slow, ~1 h) |
| 2 | `02_compute_baselines.ipynb` | Compute per-pixel percentiles → `data/*_baseline.nc` | Once per data update |
| 3 | `03_threshold_analysis.ipynb` | Load cached data, produce all plots | As often as needed (seconds) |

`03_threshold_analysis` never contacts GEE or does heavy computation. Open and run
it in seconds once the cache exists.

---

## Data source

**Zhang et al. (2022)** — Global Sub-daily Heat Temperature Dataset (GSHTD).  
GEE collection: `projects/sat-io/open-datasets/global-daily-air-temp/latin_america`  
Spatial resolution: 1 km · Temporal coverage: 2003–2020 · Variable: daily Tmax

---

## Project structure

```
heat_threshold_analysis/
├── README.md
├── requirements.txt
├── utils/
│   ├── __init__.py
│   └── heat.py          ← all shared functions; no business logic in notebooks
├── data/
│   ├── salvador_tmax.nc          (written by 01)
│   ├── teresina_tmax.nc          (written by 01)
│   ├── caceres_tmax.nc           (written by 01)
│   ├── salvador_baseline.nc      (written by 02, dims: percentile × lat × lon)
│   ├── teresina_baseline.nc      (written by 02)
│   ├── caceres_baseline.nc       (written by 02)
│   └── geobr_*_neighbourhoods_2010.gpkg  (cached on first geobr download)
├── 01_data_acquisition.ipynb
├── 02_compute_baselines.ipynb
└── 03_threshold_analysis.ipynb
```

---

## Adding a new city

1. Add an entry to `CITIES` in `utils/heat.py`:

```python
'new_city': {
    'bbox':           {'west': ..., 'east': ..., 'south': ..., 'north': ...},
    'ibge_code':      1234567,   # IBGE code, used by geobr for neighbourhood boundaries
    'label':          'City Name, Brazil',
    'gee_collection': 'projects/sat-io/open-datasets/global-daily-air-temp/latin_america',
},
```

2. Add the city key to `CITY_KEYS` at the top of `03_threshold_analysis`.

3. Run `01_data_acquisition` for the new city only:

```python
extract_city_tmax('new_city', 'data', '2003-01-01', '2020-12-31')
```

4. Re-run `02_compute_baselines` for the new city.

5. Re-run `03_threshold_analysis`.

---

## GEE authentication

```bash
earthengine authenticate
```

Then in `01_data_acquisition`, change the project name if needed:

```python
ee.Initialize(project='your-gee-project')
```

---

## Key parameters (edit in `03_threshold_analysis` Setup cell)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `YEAR` | 2020 | Year for spatial maps and quadrant plots |
| `PERCENTILE` | 90 | Relative-threshold percentile (must be in `[50,75,90,95,99]`) |
| `ABS_THRESHOLD` | 30.0 | Absolute Tmax threshold in °C |
| `THRESHOLD_RANGE` | range(20, 41) | Sweep range for sensitivity curves |
