# Global Expansion Plan: Multi-City Heat Metric Analysis

**Status:** Draft for review  
**Approach:** Stratified systematic sampling from Köppen-Geiger climate classification map  
**Purpose:** Test whether the episodic/chronic regime finding and EHF(Tmin) superiority generalise globally

---

## 1. Scientific objectives

The Brazilian analysis produced two findings that require external validation:

1. **Regime hypothesis** — heat metrics produce meaningful neighbourhood-level spatial discrimination in episodic cities (Salvador CV ≈ 0.49) but not in chronic-heat cities (Teresina/Cáceres CV ≈ 0.01), regardless of metric variant
2. **EHF(Tmin) hypothesis** — the nocturnal UHI effect creates spatial variation in chronic cities that EHF(Tmin) magnitude captures but TX90p does not (CV 10× higher in Teresina than any TX90p variant)

Extending to a systematic global sample allows us to ask:
- Does the regime hypothesis hold across climate types, or are the Brazil results idiosyncratic?
- Is EHF(Tmin) consistently better in cities where nocturnal UHI is strong (dense tropical/arid cities)?
- Where on a continuous spectrum from episodic to chronic do Mediterranean, continental, and humid subtropical cities fall?
- Does the negative TX/TN correlation seen in Cáceres (ρ = −0.452) generalise to other cities with large diurnal range?

The city list should be driven by the climate data, not by researcher intuition. Systematic sampling from the Köppen-Geiger map ensures we cover the full range of relevant climate regimes and removes selection bias.

---

## 2. Systematic city sampling methodology

### 2.1 Data sources

**Köppen-Geiger classification raster**  
Beck et al. (2018) "Present and future Köppen-Geiger climate classification maps at 1-km resolution", *Scientific Data*.  
- Download: GeoTIFF from Figshare (https://figshare.com/articles/dataset/6396959) or GloH2O portal  
- Format: ~20 MB GeoTIFF, 8-bit unsigned integer, 1 km resolution, global coverage  
- 30 distinct climate zones; numeric codes mapped to zone symbols (Af, Am, Aw, BWh, …) via legend file  
- Not yet available as a native GEE asset; used locally via `rasterio`

**Global city points**  
GHS Urban Centre Database (GHSL-UCDB R2024), European Commission Joint Research Centre.  
- 11,422 urban centres globally, defined from the GHSL settlement layer  
- Attributes include: population, built-up area, country, continent, urban centre name  
- Download: GeoJSON (~50 MB) from the JRC Human Settlement Portal  
- Rationale: consistent global definition of "urban centre" based on density thresholds, not political boundaries; preferable to GeoNames (inconsistent definitions) or Natural Earth (incomplete coverage)

### 2.2 Zone selection for heat analysis

Not all 30 Köppen zones are relevant to heat risk. The following are included and excluded:

**Included (heat-relevant):**

| Major class | Zones | Rationale |
|---|---|---|
| **A — Tropical** | Af, Am, Aw | Chronic heat; primary test bed |
| **B — Arid** | BWh, BSh | Hot desert and steppe; extreme chronic heat |
| **B — Arid (dry)** | BWk, BSk | Cold arid; heat events occur in summer, episodic |
| **C — Temperate** | Csa, Cfa | Hot Mediterranean and humid subtropical; episodic summer heat |
| **C — Temperate** | Csb, Cfb | Warm oceanic; increasingly important with climate change |
| **D — Continental** | Dfa, Dwa | Humid and monsoon-influenced continental; episodic heat events |
| **D — Continental** | Dfb, Dwb | Cooler continental; episodic events, included for completeness |

**Excluded:**
- E (polar, tundra) — minimal heat risk
- Dfc, Dfd, Dsc, Dsd, Dwc, Dwd — subarctic / very cold winter; extreme events rare and atypical
- Cfc — subpolar oceanic; very few cities, minimal heat risk

This leaves **~21 target zones** across 4 major classes.

### 2.3 Sampling algorithm

Implemented in `00_city_selection.ipynb`. Steps:

1. **Load** Beck et al. KG raster and GHSL-UCDB city points
2. **Extract** the KG zone value at each city centroid using `rasterio` point sampling
3. **Filter** to cities with GHSL population > 500,000 (ensures enough neighbourhoods for CV analysis)
4. **Group** cities by KG zone
5. **Rank** within each zone by population (largest first)
6. **Select** up to *N* cities per zone applying two diversity constraints:
   - No more than 1 city per country within a zone (avoids e.g. five Indian cities all in Aw)
   - No more than 2 cities per continent within a zone (geographic spread)
7. **Output** a candidate table and interactive map for manual review and adjustment

*N* (cities per zone) is set to **3**, giving a target of ~63 cities total across 21 zones. Three cities per zone is the minimum needed to detect whether a pattern is consistent within a zone rather than driven by a single outlier.

### 2.4 Expected output

The notebook produces a `data/city_selection.csv` with columns:

```
city_id, city_name, country, continent, koppen_zone, koppen_class,
population, lat_centroid, lon_centroid, bbox_west, bbox_east, bbox_south, bbox_north
```

This CSV becomes the source of truth for the `CITIES` registry and all downstream work. Any manual overrides (swap city A for city B within a zone) are made here, with the reason noted in a `selection_note` column, before downstream processing starts.

---

## 3. Technical architecture changes

### 3.1 What already works globally

- `utils/ehf.py` — all functions are temperature-agnostic
- All statistical and aggregation logic in `utils/heat.py` (percentile baselines, heat-day counting, `_point_in_poly_mask`)
- All analysis notebooks (05, 12, 13) — parameterised by `CITY_KEYS`
- WorldPop population extraction — global dataset, needs one-line fix (see §3.2C)

### 3.2 Changes required

**A. City registry (`utils/heat.py`)**

Extend the `CITIES` dict from `city_selection.csv` rather than hardcoding. The `ibge_code` field becomes optional. The structure for a non-Brazil city:

```python
'lagos': {
    'bbox':           (2.6, 4.0, 6.2, 6.8),
    'label':          'Lagos, Nigeria',
    'koppen':         'Aw',
    'gee_collection': 'projects/sat-io/open-datasets/global-daily-air-temp/africa',
    'ibge_code':      None,
}
```

A helper function `load_cities_from_csv(csv_path)` should auto-populate `CITIES` from the selection CSV, removing the need to hardcode entries.

**B. GSHTD GEE collection paths — confirmed**

The GSHTD dataset has five regional ImageCollections (confirmed from GEE community catalog):

```
projects/sat-io/open-datasets/global-daily-air-temp/africa
projects/sat-io/open-datasets/global-daily-air-temp/australia        ← covers Oceania
projects/sat-io/open-datasets/global-daily-air-temp/europe_asia      ← covers both Europe and Asia
projects/sat-io/open-datasets/global-daily-air-temp/latin_america
projects/sat-io/open-datasets/global-daily-air-temp/north_america
```

Note: Europe and Asia share a single collection (`europe_asia`); Oceania uses `australia`. These paths are already set in `city_selection.csv` via `CONTINENT_TO_GEE` in `00_city_selection.ipynb`. If a city falls outside GSHTD coverage, the fallback is ERA5-Land (Copernicus API, ~9 km resolution).

**C. Neighbourhood boundaries**

The `geobr` Brazil-specific loader is replaced with a general GADM-based function for non-Brazil cities. The `pygadm` package (`pip install pygadm`) retrieves GADM boundaries programmatically:

```python
import pygadm
gdf = pygadm.Items(admin='NGA', content_level=2)  # Nigeria, admin level 2
```

Admin level varies by country (level 2 in most of Africa and Asia; level 3 in USA, Europe). A `GADM_LEVEL` lookup dict in the city registry handles this. The function caches results as GeoPackage, identical to the existing Brazil pipeline.

A new function `load_neighbourhood_boundaries_global(city, data_dir)` handles this, leaving the existing `load_neighbourhood_boundaries()` (Brazil/geobr) untouched.

**D. Population extraction**

One-line fix: remove the `country='BRA'` filter from the GEE WorldPop query. No structural change.

**E. Vulnerability proxy (new)**

The Brazil analysis used census income. For global consistency, two options:

| Option | GEE asset path | Coverage | Notes |
|---|---|---|---|
| **Relative Wealth Index** | `projects/sat-io/open-datasets/facebook-relative-wealth-index` | ~93 LMICs | Best proxy for Global South; not available for USA, EU, China |
| **GHSL population density** | `JRC/GHSL/P2023A/GHS_POP` | Global | Density only, no income signal; use as weight not as vulnerability |
| **Nighttime lights (VIIRS)** | `NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG` | Global | Consistent globally; conflates industrial and residential |

Recommended approach: use Relative Wealth Index where available; nighttime lights normalised by population density elsewhere. Document the source per city in the registry.

**F. Köppen zone as an analysis dimension (new)**

Add `koppen` and `koppen_class` (first letter: A/B/C/D) to the city registry. All cross-city plots group and colour by this. A single utility function `assign_koppen(lon, lat, kg_raster_path)` extracts the zone for any point.

---

## 4. Notebook structure

| Notebook | Purpose | New / Existing |
|---|---|---|
| `00_city_selection.ipynb` | KG sampling, GHSL-UCDB join, produce `city_selection.csv` | **New** |
| `00b_data_acquisition_global.ipynb` | GEE download for all new cities (Tmax, Tmin, population, vulnerability) | **New** |
| `02_compute_baselines.ipynb` | TX90p/TN90p thresholds — runs unchanged for all cities | Existing, extend |
| `05_heat_day_analysis.ipynb` | City-level heat profiles — extend `CITY_KEYS` | Existing, extend |
| `12_hazard_metric_cov_comparison.ipynb` | TX90p/TN90p/magnitude CV — extend `CITY_KEYS` | Existing, extend |
| `13_ehf_hazard.ipynb` | EHF(Tmax) and EHF(Tmin) — extend `CITY_KEYS` | Existing, extend |
| `14_cross_city_comparison.ipynb` | Aggregate results, KG-grouped visualisations | **New** |

Notebooks 02, 05, 12, 13 require no code changes — only `CITY_KEYS` needs to include the new cities. All heavy computation is cached to NetCDF, so re-running is fast after the first pass.

**`14_cross_city_comparison.ipynb`** is the primary scientific output and produces:

- **Table**: city × metric CV matrix, sorted by Köppen zone
- **Scatter**: EHF(Tmin) magnitude CV vs TX90p days CV, one point per city, coloured by Köppen class — directly tests the main hypothesis
- **Scatter**: TX/TN Spearman ρ vs mean diurnal temperature range, to test whether the Cáceres anticorrelation generalises
- **Box plot**: neighbourhood CV of EHF(Tmin) magnitude grouped by Köppen class (A/B/C/D)
- **Time series**: cross-city EHF(Tmax) magnitude annual signal — does the 2017/2019 Brazil anomaly appear in other continents or is it regional?
- **Heatmap**: city × metric CV, sorted by both Köppen zone and mean annual temperature

---

## 5. Sequencing

### Phase 1 — City selection (1 day)
- Download Beck et al. KG GeoTIFF and GHSL-UCDB GeoJSON
- Run `00_city_selection.ipynb` to produce candidate list
- Review map and table; adjust N and diversity constraints
- Confirm final `city_selection.csv`

### Phase 2 — Infrastructure verification (1 day)
- Verify GSHTD GEE collection paths for each required region by running a single test extraction
- Check GADM admin levels for a representative sample of new cities
- Confirm pygadm installs cleanly in the project venv

### Phase 3 — Refactor utilities (1 day)
- Add `load_cities_from_csv()` to utils
- Write `load_neighbourhood_boundaries_global()` with GADM backend
- Fix WorldPop country filter
- Add `koppen` field to city registry

### Phase 4 — Data download (3–5 days, mostly GEE jobs — ~60 cities × ~10 min each)
- Run `00b_data_acquisition_global.ipynb` for all new cities
- Verify outputs (shape, date range, NaN rates, boundary polygon counts)

### Phase 5 — Analysis (2–3 days)
- Extend `CITY_KEYS` in notebooks 02, 05, 12, 13 and run
- Build and run `14_cross_city_comparison.ipynb`
- Update `HEAT_METRIC_FINDINGS.md`

**Total: ~7–10 days active work, dominated by Phase 4**

---

## 6. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| GSHTD regional GEE paths don't match expected pattern | Medium | Verify in Phase 2 before downloading; ERA5-Land (9 km, Copernicus API) as documented fallback |
| GHSL-UCDB city centroid falls in wrong KG zone (edge of zone) | Low | Use modal KG zone within 10 km radius buffer rather than point; flag edge cases in selection note |
| GADM admin level too coarse in some countries (large districts) | Medium | Per-city admin level lookup; osmnx as fallback for OSM admin boundaries |
| GEE quota exceeded for large bounding boxes | Low | Existing chunked 90-day extraction handles this; reduce chunk size if needed |
| Some KG zones have no GHSL city >500k | Low–medium (BWk, Dfb, Cfb) | Lower threshold to 200k for underrepresented zones; flag in analysis |
| 40+ city dataset makes GEE download phase very slow | Medium | Parallelise GEE extractions; accept ERA5-Land for any city where GSHTD times out |

---

## 7. Open questions for review

1. **N cities per zone** — confirmed as 3 (≈63 cities total). Note that 60 new GEE downloads at ~10 min each is roughly 10 hours of GEE job time — parallelisation or overnight batching will be needed in Phase 4.

2. **Population threshold** — 500k is a pragmatic floor for neighbourhood-level CV analysis. Should zones with no city above 500k (possible for BWk, some Dfb regions) be excluded or have the threshold relaxed?

3. **GSHTD vs ERA5-Land fallback** — if GSHTD is unavailable for a region, should those cities be included with ERA5-Land at lower resolution, or excluded to keep the dataset homogeneous? Using ERA5-Land introduces a confound (resolution difference) but maximises zone coverage.

4. **Vulnerability proxy** — Relative Wealth Index + nighttime lights composite, or drop vulnerability from the global analysis and focus on the heat metric CV question alone? The cross-city comparison is primarily about heat metrics; vulnerability comes in for the neighbourhood ranking question.

5. **Temporal range** — should the global cities use the same 2003–2020 window as the Brazil analysis for comparability, or extend to the latest available year? GSHTD coverage ends at different dates by region.

---

*This plan supersedes the previous version. No code changes have been made. Implementation begins after Phase 1 (city selection) is reviewed and `city_selection.csv` is approved.*
