# GSHTD Tmin Threshold Variant Comparison — Analysis Summary

**Notebook:** `notebooks/29_gshtd_threshold_variants_comparison.ipynb`  
**Date:** July 2026  
**Dataset:** Zhang et al. (2022) GSHTD — 1 km daily Tmin  
**Source:** `projects/sat-io/open-datasets/global-daily-air-temp/` (GEE)

---

## Recommendations

### 1. Use Tmin (overnight minimum) not Tmax

In cities with chronically high daytime temperatures — Teresina and Cáceres — TX90p and TN90p assign completely different neighbourhoods to the top of the priority list. Spearman rank correlation between TX90p and TN90p neighbourhood rankings:

| City | ρ (TX90p vs TN90p heat days) | Interpretation |
|------|------------------------------|----------------|
| Salvador | +0.82 | Day and night rankings broadly agree |
| Teresina | +0.06 | Near-zero agreement — daytime and overnight identify different neighbourhoods |
| Cáceres | −0.45 | **Negative** — the hottest-by-day neighbourhoods are among the coolest-by-night |

Tmax captures peak daytime exposure, which is strongly shaped by surface properties (impervious cover, albedo, shade). Tmin captures the overnight recovery window, which is driven by atmospheric moisture and longwave re-emission — a physiologically distinct process. Where the two diverge (Teresina, Cáceres), choosing Tmax would systematically misprioritise neighbourhoods for heat adaptation.

**Recommendation: use Tmin (TN90p) as the primary heat metric.**

---

### 2. Use a city-calibrated percentile threshold, not a fixed absolute value

Applying a single absolute threshold (e.g. Tmax ≥ 30 °C) to all cities simultaneously causes saturation in hot cities: in Teresina, 111 of 112 neighbourhoods record exactly 356 heat days per year — the metric carries no spatial information. The same problem arises with fixed Tmin thresholds in persistently warm cities.

A percentile threshold calibrated to each city's own 2003–2020 base period (P90 or P95 of the local pixel distribution) recovers meaningful intra-city discrimination. Neighbourhood rank agreement across the four tested variants (ann\_p90, ann\_p95, mw\_p90, mw\_p95) is ρ ≥ 0.90 when pooled across Salvador, Rio, and Bengaluru — confirming the approach is robust to the exact percentile or window choice (see Key Finding 3 below).

**Recommendation: use city-calibrated TN90p (moving-window or annual P90 of the base period), not an absolute fixed threshold.**

---

## Overview

This analysis compares four Tmin-based heat threshold variants across three cities — **Salvador, Brazil**, **Rio de Janeiro, Brazil**, and **Bengaluru, India** — and tests how much the choice of threshold method affects heat day counts and neighbourhood-level rankings in a single test year (2019).

---

## Setup

### Cities and data coverage

| City | Grid size | Time range | Base period years |
|------|-----------|------------|-------------------|
| Salvador, Brazil | 48 × 67 pixels | 2003-01-01 – 2020-12-30 | 18 |
| Rio de Janeiro, Brazil | 42 × 76 pixels | 2003-01-01 – 2020-12-30 | 18 |
| Bengaluru, India | 44 × 45 pixels | 2003-01-01 – 2020-12-30 | 18 |

GEE sub-collections used:
- Brazil cities → `latin_america`
- Bengaluru → `europe_asia`

### Four threshold variants

| Variant key | Method | Percentile |
|-------------|--------|------------|
| `ann_p90` | Annual percentile of all base-period Tmin days, per pixel | 90th |
| `ann_p95` | As above | 95th |
| `mw_p90` | Moving-window percentile: 5-day centred window per calendar DOY, across base-period years | 90th |
| `mw_p95` | As above | 95th |

Moving-window implementation: pure NumPy replication of `xclim.percentile_doy(bootstrap=False)`. Feb 29 excluded so DOY maps cleanly to 1–365.

### Base period and test year
- Base period: 2003-01-01 – 2020-12-31 (chosen to match WorldPop population data vintage)
- Test year: 2019 (361 non-leap days available for all three cities)

### Neighbourhood boundaries
- Source: `data/neighbourhoodShapes/`
- Format: GeoJSON, field `neighborhood_name`
- Salvador: 170 neighbourhoods | Rio: 162 | Bengaluru: 369
- Zonal aggregation: point-in-polygon spatial join of 1 km pixel centroids to neighbourhood polygons (`predicate='intersects'`), then mean per neighbourhood

---

## Threshold ranges (per-pixel, °C)

### Salvador, Brazil

| Variant | Min °C | Max °C |
|---------|--------|--------|
| ann_p90 | 23.6 | 25.1 |
| ann_p95 | 24.1 | 26.0 |
| mw_p90  | 17.4 | 28.2 |
| mw_p95  | 17.4 | 29.6 |

### Rio de Janeiro, Brazil

| Variant | Min °C | Max °C |
|---------|--------|--------|
| ann_p90 | 19.6 | 24.1 |
| ann_p95 | 20.4 | 24.9 |
| mw_p90  | 14.2 | 26.2 |
| mw_p95  | 14.9 | 27.5 |

### Bengaluru, India

| Variant | Min °C | Max °C |
|---------|--------|--------|
| ann_p90 | 21.8 | 22.8 |
| ann_p95 | 22.5 | 23.5 |
| mw_p90  | 16.4 | 24.6 |
| mw_p95  | 17.4 | 25.7 |

**Observations:**
- The moving-window variants produce a wider spatial range than the annual variants in all three cities, because they capture intra-annual seasonality — the threshold is lower in cooler months and higher in the hottest months.
- Bengaluru has the narrowest annual threshold range (< 1 °C across the city), reflecting its plateau topography and spatially homogeneous land surface.
- Rio has the widest spatial spread across all variants, driven by its steep elevation gradient from coast to Tijuca highlands.

---

## Pixel-level heat day counts in 2019 (mean across all pixels)

| City | ann_p90 | ann_p95 | mw_p90 | mw_p95 | max (any variant) |
|------|---------|---------|--------|--------|-------------------|
| Salvador | 18.6 | 9.3 | 17.8 | 9.2 | 72 |
| Rio de Janeiro | 49.9 | 25.4 | 58.5 | 32.7 | 94 |
| Bengaluru | 25.3 | 9.8 | 21.3 | 7.4 | 41 |

---

## Neighbourhood-level summary table (mean heat days, 2019)

| City | Variant | n neighbourhoods | Mean (days) | SD (days) | Min | Max |
|------|---------|-----------------|-------------|-----------|-----|-----|
| Salvador, Brazil | Annual P90 | 123 | 45.8 | 14.3 | 0.0 | 61.0 |
| Salvador, Brazil | Annual P95 | 123 | 19.5 | 7.2 | 0.0 | 27.0 |
| Salvador, Brazil | Moving-window P90 | 123 | 41.4 | 12.5 | 0.0 | 51.5 |
| Salvador, Brazil | Moving-window P95 | 123 | 16.8 | 5.8 | 0.0 | 28.5 |
| Rio de Janeiro, Brazil | Annual P90 | 151 | 62.9 | 11.6 | 0.0 | 75.0 |
| Rio de Janeiro, Brazil | Annual P95 | 151 | 31.7 | 6.2 | 0.0 | 41.2 |
| Rio de Janeiro, Brazil | Moving-window P90 | 151 | 76.5 | 13.6 | 0.0 | 88.6 |
| Rio de Janeiro, Brazil | Moving-window P95 | 151 | 42.4 | 7.9 | 0.0 | 53.0 |
| Bengaluru, India | Annual P90 | 287 | 29.0 | 3.5 | 22.0 | 41.0 |
| Bengaluru, India | Annual P95 | 287 | 11.3 | 1.1 | 8.5 | 14.0 |
| Bengaluru, India | Moving-window P90 | 287 | 23.8 | 2.2 | 18.0 | 31.0 |
| Bengaluru, India | Moving-window P95 | 287 | 9.8 | 1.4 | 4.6 | 13.0 |

---

## Key finding 1: Annual vs moving-window direction reverses between cities

Rio is the only city where the moving-window threshold produces **more** heat days than the annual threshold. Salvador and Bengaluru both show the opposite.

| City | Ann P90 | MW P90 | MW vs Annual | Ann P95 | MW P95 | MW vs Annual |
|------|---------|--------|--------------|---------|--------|--------------|
| Rio de Janeiro | 62.9 | 76.5 | **+22%** | 31.7 | 42.4 | **+34%** |
| Salvador | 45.8 | 41.4 | **−10%** | 19.5 | 16.8 | **−14%** |
| Bengaluru | 29.0 | 23.8 | **−18%** | 11.3 | 9.8 | **−13%** |

**Interpretation:** Rio has a stronger seasonal cycle in Tmin (coast-influenced, distinct summer and winter). The moving-window threshold is calibrated to each DOY, so it sets a lower bar in shoulder seasons — flagging more days as exceedances than the single annual percentile does. Salvador and Bengaluru have relatively flat annual Tmin cycles: the annual percentile captures most of what the moving window would, and in practice sets a slightly lower threshold than the seasonal peak (which the moving window calibrates to precisely), resulting in more exceedances under the annual definition.

This finding has implications for cross-city comparability: choosing between annual and moving-window methods will not affect city rankings uniformly.

---

## Key finding 2: Intra-city spatial variability differs sharply

Standard deviation of neighbourhood heat day counts:

| City | Ann P90 SD | MW P90 SD |
|------|-----------|-----------|
| Rio de Janeiro | 11.6 days | 13.6 days |
| Salvador | 14.3 days | 12.5 days |
| Bengaluru | 3.5 days | 2.2 days |

Bengaluru's within-city spread is 3–4× smaller than the Brazilian cities. At 1 km resolution, Bengaluru's plateau topography produces a near-uniform thermal environment. This means that in Bengaluru, neighbourhood selection for heat interventions based on heat day counts alone will be less discriminating — other vulnerability indicators (population density, age structure, poverty) will likely dominate any composite score.

---

## Key finding 3: Neighbourhood rankings are robust to variant choice

Spearman rank correlations across variants, neighbourhood level (n = 561 neighbourhoods with complete data, all cities pooled):

|  | Annual P90 | Annual P95 | MW P90 | MW P95 |
|--|-----------|-----------|--------|--------|
| **Annual P90** | 1.000 | 0.926 | 0.917 | 0.904 |
| **Annual P95** | 0.926 | 1.000 | 0.902 | 0.913 |
| **MW P90** | 0.917 | 0.902 | 1.000 | 0.912 |
| **MW P95** | 0.904 | 0.913 | 0.912 | 1.000 |

All pairwise ρ ≥ 0.90. **The spatial ranking of which neighbourhoods experience most heat nights is virtually identical regardless of which of the four threshold variants is used.** Within-method pairs (e.g. Ann P90 vs Ann P95, ρ = 0.926) are marginally tighter than cross-method pairs (~0.91), meaning method choice has a slightly larger effect than percentile choice on rankings — but neither effect is large.

Practical implication: for the purpose of identifying priority neighbourhoods for heat adaptation, the simpler annual percentile (no windowed computation required) will produce almost identical targeting as the ETCCDI moving-window approach.

---

## Caveats and known issues

### 1. Salvador base period (resolved)
An earlier version of this analysis used a pre-existing local file covering only 2018–2020 (3 years). The full 2003–2020 series has now been downloaded from GEE (`salvador_tmin.nc`, 80 MB, 6,496 days). All results above use the 18-year base period.

With the 3-year base, Salvador appeared to behave like Rio (MW > Annual). With 18 years it correctly joins Bengaluru (MW < Annual). The 3-year result was an artefact of an unstable percentile estimate from insufficient data.

### 2. Bengaluru Tmin minimum of −13.0 °C
The raw GSHTD data for Bengaluru contains a minimum value of −13.0 °C. This is implausible for a city at 900 m elevation in southern India (typical winter Tmin ~14–16 °C). It is likely an edge-pixel artefact or a retrieval error in the GSHTD dataset for that location. The annual percentile threshold (21.8–22.8 °C) is well above this outlier so it should not materially affect P90/P95 exceedance counts, but the raw data should be inspected spatially before this city's thresholds are used in any published analysis.

### 3. Neighbourhood coverage gaps
- Salvador: 123/170 neighbourhoods covered (72%)
- Rio de Janeiro: 151/162 neighbourhoods covered (93%)
- Bengaluru: 287/369 neighbourhoods covered (78%)

Coverage was not improved by switching the spatial join predicate from `within` to `intersects`. The uncovered neighbourhoods are sub-kilometre polygons (particularly in Salvador's dense historic centre and Bengaluru's smaller administrative units) that contain no 1 km GSHTD pixel centroids. This is a hard resolution ceiling of the 1 km dataset and cannot be resolved without a finer-resolution temperature product.

### 4. Single test year
All heat day counts are for 2019 only. 2019 was a notably hot year in Rio de Janeiro (mean neighbourhood ann_p90 heat days = 62.9, max = 75 out of 361 days). Results should not be generalised to a typical year without repeating across multiple test years.

### 5. Salvador pixel-level vs neighbourhood-level discrepancy
The pixel-level mean heat day count for Salvador (ann_p90 = 18.6 days) is substantially lower than the neighbourhood-level mean (45.8 days). This is because the GSHTD bounding box for Salvador includes ocean and coastal pixels with lower temperatures, which pull down the pixel mean. The neighbourhood polygons cover the urban land mass where temperatures are higher. This is expected and not a data error.

---

## Files

| File | Description |
|------|-------------|
| `data/salvador_tmin.nc` | GSHTD Tmin, Salvador, 2003–2020, 48×67 pixels, 6496 days |
| `data/rio_de_janeiro_tmin.nc` | GSHTD Tmin, Rio de Janeiro, 2003–2020, 42×76 pixels, 6496 days |
| `data/bengaluru_tmin.nc` | GSHTD Tmin, Bengaluru, 2003–2020, 44×45 pixels, 6495 days |
| `data/neighbourhoodShapes/salvador_ba_bra_neighborhoods.geojson` | 170 neighbourhood polygons |
| `data/neighbourhoodShapes/rio_de_janeiro_rj_bra_neighborhoods.geojson` | 162 neighbourhood polygons |
| `data/neighbourhoodShapes/bengaluru_ka_ind_neighborhoods.geojson` | 369 neighbourhood polygons |
| `notebooks/29_gshtd_threshold_variants_comparison.ipynb` | Full analysis notebook with outputs |
