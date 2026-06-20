# HeatInsights: Notebook Analysis Summary
## Methods Explored, Findings, and Recommendations for Heat Risk Platform Development

*Updated: June 2026 | Cities: Salvador, Teresina, Cáceres (Brazil) | Notebooks: 00–16*

---

## Overview

This document summarises findings from the heat threshold analysis notebook series covering three Brazilian cities across distinct climate regimes. The analysis explored how to characterise urban heat risk using the standard **Hazard → Exposure → Vulnerability** framework, tested multiple temperature metrics, and investigated what drives neighbourhood-level risk rankings. Findings are intended to inform architectural decisions for the multi-city heat risk platform under development.

The central analytical problem is **spatial discrimination**: for a hazard metric to be useful at neighbourhood scale, it must produce meaningfully different values across neighbourhoods within the same city. The primary diagnostic is the **coefficient of variation (CV = σ/μ)** across neighbourhoods. A metric with CV < 0.05 is effectively spatially flat — every neighbourhood gets the same score regardless of its actual thermal character. The findings below map which metrics fail, which succeed, and why.

---

## 1. Data Sources and Spatial Scales

| Dataset | Resolution | Period | Coverage | Notes |
|---|---|---|---|---|
| GSHTD (Zhang et al. 2022) | 1 km | 2003–2020 | Global | Primary temperature source; accessed via GEE |
| VITO UrbClim | 100 m | 2008–2017 | 142 cities | High-resolution urban climate model; proprietary licence |
| WorldPop | 100 m → 1 km | 2003–2020 | Global | Annual population grids; resampled to match temperature resolution |
| ERA5-Land | ~9 km | Full record | Global | Reanalysis; used for validation and acquisition fallback |
| Brazilian Census 2022 | Census sector | 2022 | Brazil | Household head income (`renda_responsavel`, BRL) |
| GHSL-UCDB R2024 | — | — | Global | Urban centre database for city selection (11,422 cities) |

### 1.1 The Three Cities

These cities were selected to represent contrasting climate regimes, stress-testing whether any single metric works across contexts:

**Salvador (Bahia, Brazil) — coastal, episodic heat**
- Atlantic coast; trade-wind driven sea breeze moderates daytime temperatures in coastal neighbourhoods
- 1 km Tmax P90 ≈ 32.9 °C; ~63 days/year above 30 °C
- Meaningful intra-urban thermal gradient: coastal zones vs inland periphery
- Population ~2.9 million; 22 administrative neighbourhoods in analysis

**Teresina (Piauí, Brazil) — semi-arid interior, chronic heat**
- Located inland at the confluence of the Parnaíba and Poti rivers; one of the hottest cities in Brazil
- 1 km Tmax P90 ≈ 36.9 °C; ~322 days/year above 30 °C
- Daytime Tmax is near-uniform across the urban area at 1 km — almost no spatial gradient
- Population ~900,000; 112 administrative neighbourhoods in analysis

**Cáceres (Mato Grosso, Brazil) — hot/dry savanna (Cerrado)**
- Located in the Pantanal transition zone; hot, dry winters and hot, wet summers
- 1 km Tmax P90 ≈ 35.8 °C; ~278 days/year above 30 °C
- Notable anti-correlation between daytime and nighttime heat across neighbourhoods (see Section 2.1C)
- Population ~100,000; 43 administrative neighbourhoods in analysis

### 1.2 Why CV is the Key Diagnostic

At the neighbourhood level, a metric's usefulness for prioritisation depends on it being able to rank neighbourhoods differently. If every neighbourhood has a nearly identical value, the metric cannot inform where to target interventions. The CV threshold of ~0.05 used throughout this analysis is a practical cutoff below which ranking differences are within measurement noise. For context:

- Income CV ≈ 1.3 — very high spatial variation; income maps are informative
- Population CV ≈ 1.0 — high variation; population maps are informative
- TX90p heat days (Salvador) CV ≈ 0.48 — moderate; useful for prioritisation
- TX90p heat days (Teresina) CV ≈ 0.009 — effectively zero; useless for prioritisation

---

## 2. Hazard

### 2.1 Metrics Tested

Five metric families were explored in order of increasing methodological sophistication. The core challenge is that standard heat metrics fail in chronically hot cities because daytime maximum temperature (Tmax) is spatially homogenised by strong solar forcing — every neighbourhood experiences essentially the same daytime heat at 1 km resolution. The metrics that succeed do so by exploiting nighttime temperature, where the urban heat island (UHI) creates genuine spatial gradients.

---

#### **A. Absolute Threshold (days ≥ 30 °C, Tmax)**

The simplest approach: count days Tmax exceeds a fixed temperature. Clinically motivated by evidence that heat-related illness risk rises steeply above 30 °C in many contexts.

| City | Days/yr ≥ 30 °C | Neighbourhood CV | Assessment |
|---|---|---|---|
| Salvador | 63 | 0.44 | Works; meaningful spatial signal |
| Teresina | 322 | 0.01 | **Fails** — threshold saturated |
| Cáceres | 278 | 0.01 | **Fails** — threshold saturated |

**Why it fails in Teresina and Cáceres:** In cities where nearly every day exceeds 30 °C, all neighbourhoods accumulate near-identical counts. The threshold is crossed so frequently that neighbourhood-level variation in temperature (which is small at 1 km) cannot register as variation in day counts. The result is a spatially flat map that carries no prioritisation information.

**Costs/Benefits:**
- Simple to compute; easy to explain to non-technical audiences ("X days above 30 °C per year")
- Directly actionable in episodic/temperate cities where the threshold is not saturated
- Completely unusable in chronically hot cities — provides no spatial signal
- Threshold is globally fixed; not calibrated to local physiology or acclimatisation

---

#### **B. Flat Percentile Thresholds (P90, P95, P99 of full record)**

A city-wide or per-pixel percentile computed over the full 2003–2020 record. By using a relative threshold, this approach removes mean-temperature differences between cities, making counts more comparable across climates.

| City | P90 threshold | P90 days/yr | Neighbourhood CV (P90) |
|---|---|---|---|
| Salvador | ~32.9 °C | 11.1 | ~0.64 |
| Teresina | ~36.9 °C | 33.7 | ~0.01 |
| Cáceres | ~35.8 °C | 34.2 | ~0.01 |

**Why the relative threshold helps Salvador but not the hot cities:** In Salvador, the sea-breeze effect creates genuine neighbourhood-level variation in Tmax. Coastal areas have systematically lower Tmax than inland areas, so exceedance counts vary meaningfully. In Teresina and Cáceres, Tmax is spatially flat at 1 km resolution even before the threshold is applied — the percentile is computed per-pixel but all pixels have near-identical distributions, so exceedance counts remain near-identical after the threshold is applied.

**P99 sample-size problem:** With a 5-day centred window baseline and an 18-year record, each calendar day has approximately 90 observations per pixel. At P99, only ~1 observation per pixel-day falls above threshold, giving unstable estimates. P99 is not recommended for this dataset and baseline period.

**Costs/Benefits:**
- Removes inter-city absolute bias; counts are comparable within the climate-relative frame
- Salvador CV improves meaningfully over absolute threshold (0.64 > 0.44)
- Does not resolve the spatial flatness problem in Teresina and Cáceres
- Per-pixel percentiles computed over short baselines are sensitive to local data artefacts

---

#### **C. ETCCDI Calendar-Day Percentile (TX90p / TN90p)**

The ETCCDI TX90p standard (used by WMO and IPCC): a per-pixel, per-day-of-year threshold computed using a centred 5-day window across the 2003–2020 baseline, implemented via xclim. The seasonal adjustment means the threshold varies by day of year (standard deviation ~1.5–3 °C across the annual cycle), better capturing what is "anomalously hot" at different times of year.

| City | TX90p CV | TN90p CV | Notes |
|---|---|---|---|
| Salvador | 0.485 | 0.481 | Moderate spatial variation; day and night consistent |
| Teresina | 0.009 | 0.010 | Spatially flat for both |
| Cáceres | 0.008 | 0.010 | Spatially flat for both |

**Daytime vs Nighttime Ranking Consistency (Spearman ρ):**

| City | ρ(TX90p hd, TN90p hd) | Interpretation |
|---|---|---|
| Salvador | +0.82 | Same neighbourhoods hot by day and night |
| Teresina | +0.06 | Different spatial patterns; essentially uncorrelated |
| **Cáceres** | **−0.45** | **Anti-correlated** — hot-day ≠ hot-night neighbourhoods |

**The Cáceres anti-correlation is an important physical finding.** In this semi-arid savanna environment, exposed/paved areas (high albedo, low thermal mass) heat strongly under daytime solar forcing but cool rapidly by longwave emission overnight. Vegetated and humid areas (parks, river margins, higher-density urban cores with residual moisture) maintain warmth overnight. The consequence for the platform: TX90p and TN90p **cannot be averaged or combined** in Cáceres — they capture distinct physical mechanisms and flag different neighbourhoods. They must be stored and presented as separate layers.

**Why the ETCCDI definition still fails at 1 km in hot cities:** The TX90p threshold is computed per-pixel from each pixel's own distribution. If all pixels have near-identical Tmax distributions — as is the case across a flat 1 km urban grid in a chronically hot city — then the thresholds are near-identical, and exceedance counts are near-identical. The relative threshold cannot create spatial variation where the underlying data has none.

**Costs/Benefits:**
- Peer-reviewed ETCCDI standard; directly comparable to published literature and IPCC indices
- Seasonal adjustment reduces false-positive counts in cities with strong annual temperature cycles
- Still fails for spatial discrimination in Teresina and Cáceres at 1 km — the fundamental limitation is data spatial homogeneity, not the threshold definition
- TN90p reveals the Cáceres anti-correlation finding that has architectural implications (separate layers)

---

#### **D. Excess Heat Factor — EHF(Tmax) and EHF(Tmin)**

EHF (Nairn & Fawcett 2013) was developed for epidemiological modelling of Australian heatwave mortality and has a two-component structure designed to capture both climatological significance and physiological acclimatisation:

- **EHI_sig** = (mean of T over days t, t−1, t−2) − T₉₅ of all such 3-day means across the baseline record. Measures how anomalous the current period is relative to the city's full thermal history.
- **EHI_accl** = (mean of T over days t, t−1, t−2) − (mean of T over preceding 30 days). Measures how anomalous the current period is relative to *recent* conditions — capturing how well-acclimatised the population is likely to be.
- **EHF** = EHI_sig × max(1, EHI_accl). The multiplicative structure means EHF is large only when both components are positive simultaneously: the period is both historically extreme *and* the population has not been recently acclimatised to such heat.
- **Heatwave identification:** EHF > 0 for ≥ 3 consecutive days
- **Annual magnitude:** sum of positive EHF values across all days in a year

The key innovation over simple threshold metrics is the **30-day acclimatisation window**. This rolling mean captures the thermal context immediately preceding each period, amplifying events where heat arrives suddenly after a cooler spell. In urban contexts, this window also interacts with the nocturnal UHI: neighbourhoods where Tmin stays persistently elevated have shorter "cool-down" periods, meaning their 30-day rolling mean stays elevated, which suppresses EHI_accl — they are thermally acclimatised. Peri-urban areas that cool at night have lower rolling means and therefore higher EHI_accl when heat arrives.

**Neighbourhood CV comparison:**

| City | TX90p days CV | EHF(Tmax) mag CV | EHF(Tmin) mag CV |
|---|---|---|---|
| Salvador | 0.485 | 0.389 | 0.431 |
| Teresina | 0.009 | 0.020 | **0.141** |
| Cáceres | 0.008 | 0.009 | **0.073** |

**EHF(Tmin) was the first metric to produce meaningful spatial discrimination in chronically hot cities**, achieving ~15× improvement in Teresina (0.009 → 0.141) and ~9× in Cáceres (0.008 → 0.073). The mechanism is the **nocturnal urban heat island**: daytime Tmax is spatially homogenised by strong solar forcing across the entire urban area, but Tmin reflects local surface energy balance — dense urban cores with high thermal mass and impervious cover stay warm overnight while green, peri-urban, or well-ventilated areas cool. EHF amplifies these contrasts through both the T95 baseline (which is lower for cooler peri-urban areas) and the 30-day acclimatisation window.

Note that EHF(Tmax) provides almost no improvement over TX90p in Teresina and Cáceres (CV 0.020 and 0.009 respectively) — the daytime signal remains flat regardless of the EHF formulation.

**Extreme year amplification (EHF Tmax annual magnitude):**

| City | 2017 magnitude | 2019 magnitude | Long-run mean | Peak ratio |
|---|---|---|---|---|
| Salvador | 2,132 | 1,698 | 255 | ~8× |
| Teresina | 1,662 | 1,481 | 198 | ~8× |
| Cáceres | 1,488 | 514 | 138 | ~11× |

2017 and 2019 stand out as exceptional heat years across all three cities, consistent with La Niña-driven drought conditions across tropical Brazil. EHF's multiplicative structure amplifies these events strongly: when both significance and acclimatisation anomaly are simultaneously elevated, the product is much larger than additive metrics would suggest. Platform users should be made aware of these outlier years to avoid misinterpreting long-run means.

**Costs/Benefits:**
- EHF(Tmin) was, prior to CDD analysis (Section 2.1E), the best-performing hazard metric for neighbourhood-level discrimination in chronically hot cities
- Requires complete Tmax **and** Tmin time series; computationally more intensive than count-based metrics
- The 30-day rolling window requires at least 30 days of data before the first valid EHF value (lead-in requirement for streaming pipelines)
- The T95 baseline requires computing 3-day means across the full historical record before the annual metric can be derived
- Multiplicative magnitude units (°C²·days) are not intuitive; raw values should never be presented directly — express as percentile rank within city
- The 30-day acclimatisation window was calibrated on Australian temperate cities; its optimality for tropical Brazilian cities has not been validated
- EHF's link to mortality has not been validated against Brazilian health outcome data — a significant open question before deploying as a public-facing metric

---

#### **E. Cooling Degree Days (CDD, Tmin) — Notebooks 15–16**

Cooling degree days accumulate the **magnitude of excess temperature** above a fixed absolute threshold across all days in a year, rather than simply counting how many days exceeded it:

`CDD_threshold = Σ max(0, Tmin_t − threshold)` summed over all days t in year

Two thresholds were tested, both grounded in the physiological literature on nocturnal recovery from heat stress:
- **CDD20** (threshold 20 °C): based on the ETCCDI tropical night definition (TR20); 20 °C is broadly the point below which the body can achieve adequate overnight cooling
- **CDD25** (threshold 25 °C): a more selective threshold used in heat health studies for South and Southeast Asia and Brazil, where populations are more acclimatised to warm nights

For each threshold, the CDD metric was compared against the simple tropical night count (TR20 / TR25) to isolate the effect of accumulating intensity vs merely counting exceedances.

**City-wide mean annual values (2003–2020):**

| City | CDD20 (°C·d) | TR20 nights/yr | CDD25 (°C·d) | TR25 nights/yr |
|---|---|---|---|---|
| Salvador | 263 | 103 | 4.5 | 4.9 |
| Teresina | 1,179 | 356 | 8.1 | 16.3 |
| Cáceres | 631 | 242 | 3.3 | 5.8 |

The very low CDD25 and TR25 values for Salvador and Cáceres reflect that their Tmin climatologies rarely reach 25 °C — the 25 °C threshold is near the upper tail of their Tmin distribution. In Teresina, Tmin routinely exceeds 20 °C (356 nights/yr) but only occasionally 25 °C.

**Neighbourhood CV — full metric comparison:**

| City | TR20 count CV | CDD20 CV | TR25 count CV | CDD25 CV |
|---|---|---|---|---|
| Salvador | 0.478 | 0.458 | 0.427 | 0.414 |
| Teresina | 0.004 | 0.039 | 0.219 | **0.284** |
| Cáceres | 0.012 | 0.031 | 0.157 | **0.213** |

**CDD20 vs TR20 (20 °C threshold):** In Teresina and Cáceres, both TR20 count and CDD20 are near-saturated (CV < 0.05). Nearly every neighbourhood exceeds 20 °C on virtually every night of the year, leaving neither the count nor the accumulated excess with meaningful spatial variation. In Salvador, both metrics perform similarly (CV ~0.46–0.48) — the 20 °C threshold is not saturated there.

**CDD25 vs TR25 (25 °C threshold):** The 25 °C threshold is more selective. In Teresina and Cáceres, it is crossed on only a subset of nights and in a spatially variable way, creating useful discrimination. CDD25 achieves a further 30–36% improvement over TR25 count by accumulating intensity: neighbourhoods where Tmin persistently exceeds 25 °C by several degrees score disproportionately higher than those where Tmin barely crosses 25 °C.

**The key finding: CDD25 outperforms EHF(Tmin).**

| City | EHF(Tmin) CV (nb13) | CDD25 CV (nb16) | Ratio CDD25/EHF |
|---|---|---|---|
| Salvador | 0.431 | 0.414 | 0.96× (equivalent) |
| Teresina | 0.141 | **0.284** | **2.0× CDD wins** |
| Cáceres | 0.073 | **0.213** | **2.9× CDD wins** |

CDD25 substantially outperforms EHF(Tmin) in both chronic heat cities. This is counter-intuitive given EHF's more sophisticated structure, but the mechanism is clear: EHF uses T95 of 3-day means as its climatological baseline, which is a *relative* threshold computed from each pixel's own history. This means it partly normalises away the absolute temperature differences between neighbourhoods — the same flaw that makes TX90p and TN90p spatially flat. CDD25 uses a *fixed* absolute threshold (25 °C) and accumulates intensity above it; spatial variation in Tmin above 25 °C compounds over 300+ nights per year in Teresina, amplifying what appear to be small differences in mean Tmin into large differences in annual CDD.

In Salvador, where the 25 °C threshold is rarely crossed and both metrics have similar CV (~0.41–0.43), CDD25 and EHF(Tmin) are essentially equivalent.

**Why CDD25 is preferred over EHF(Tmin) where it performs equivalently or better:**
- CDD25 is directly interpretable: "this neighbourhood accumulates X °C·days above 25 °C per year"
- Requires only Tmin — no need for Tmax, T95 baseline of 3-day means, or 30-day rolling window
- Computationally simple; no lead-in requirement; no multiplicative structure producing large outlier years
- Threshold is physiologically grounded in the heat-health literature for tropical populations

**When EHF(Tmin) may still be preferred:**
- In cities where the 25 °C threshold is rarely crossed (e.g. cooler cities in the global expansion), CDD25 will accumulate near-zero values and EHF may remain the only discriminating metric
- EHF's acclimatisation framing is meaningful for public health communication about sudden heat events, even if its spatial CV is lower

**Costs/Benefits of CDD25:**
- Strong spatial discrimination in chronically hot cities — the first simple metric to outperform EHF(Tmin)
- Physiologically grounded; threshold choice (25 °C) is documented in literature
- Communicable: units are °C·days, interpretable without statistical training
- Sensitive to threshold choice — CDD20 saturates where CDD25 does not; the appropriate threshold varies by climate regime
- Does not capture acclimatisation dynamics (a population in a neighbourhood with CDD25 = 500 may be better acclimatised than one in a city experiencing its first CDD25 = 100 event)
- Threshold of 25 °C is calibrated for tropical populations; may not be appropriate for cities where Tmin rarely reaches 25 °C — in these cases CDD20 or a locally-tuned threshold is needed

---

### 2.2 Complete CV Comparison Across All Metrics

The table below consolidates all CV values at neighbourhood level, enabling direct comparison of every metric tested.

| City | Abs hd (≥30°C) | TX90p hd | EHF(Tmax) | EHF(Tmin) | TR20 count | CDD20 | TR25 count | CDD25 |
|---|---|---|---|---|---|---|---|---|
| Salvador | 0.44 | 0.485 | 0.389 | 0.431 | 0.478 | 0.458 | 0.427 | 0.414 |
| Teresina | 0.01 | 0.009 | 0.020 | 0.141 | 0.004 | 0.039 | 0.219 | **0.284** |
| Cáceres | 0.01 | 0.008 | 0.009 | 0.073 | 0.012 | 0.031 | 0.157 | **0.213** |

**Reading this table:** For Salvador, most metrics are informative (CV 0.39–0.49). For Teresina and Cáceres, only EHF(Tmin), TR25 count, and CDD25 produce CV above 0.05. CDD25 is the clear winner in both chronic cities.

---

### 2.3 Resolution: Does 100 m Fix the Problem? (Notebook 08)

VITO UrbClim 100 m data for Salvador (2008–2017) was used to test whether the spatial flatness observed in Teresina and Cáceres is a resolution artefact — i.e., whether coarser 1 km pixels are averaging over real sub-pixel variation.

| Resolution | CV: abs heat days | CV: TX90p heat days |
|---|---|---|
| 1 km (GSHTD) | 0.443 | 0.644 |
| 100 m (UrbClim) | **0.815** | 0.015 |

**Key findings:**
- Absolute heat days improve dramatically at 100 m (CV 0.44 → 0.82) — UrbClim resolves the nocturnal and daytime UHI at the block scale
- TX90p gets *worse* at 100 m (CV 0.64 → 0.015) — the relative threshold normalises out the very signal that resolution reveals. At 100 m, each pixel's own percentile threshold captures its own UHI intensity, so exceedances are equalised across the city
- Person-day population dominance is unchanged at 100 m: ρ(pop, TX90p person-days) = +0.996

**UrbClim Tmin dataset bias:** When applying the same 20 °C and 25 °C absolute thresholds to UrbClim Tmin (for the tropical nights analysis), UrbClim produces near-complete saturation at 20 °C (TR20 ~362 nights/yr, CV ≈ 0) compared to GSHTD (TR20 ~103 nights/yr, CV ≈ 0.43). This is not a resolution effect — it reflects a documented ~3 °C warm bias in UrbClim Tmin relative to GSHTD. The two datasets cannot be compared using the same absolute threshold; a bias-corrected threshold (e.g. TR23 on UrbClim ≈ TR20 on GSHTD) would be needed for a fair comparison.

**Implication for developers:** 100 m resolution benefits absolute-threshold hazard maps significantly, but actively harms relative-percentile metrics. The choice of metric must precede the choice of resolution. For CDD25 specifically, higher resolution would be expected to increase CV further (as more of the within-city Tmin gradient is resolved), but this has not yet been tested.

---

### 2.4 ERA5 vs GSHTD Comparison (Notebook 14)

ERA5-Land (~9 km) was evaluated as a fallback data source for the global expansion, where GSHTD coverage via GEE may be incomplete for some regions or periods.

Key findings from the Salvador comparison:
- GSHTD Tmax is ~2.5 °C warmer than UrbClim; ERA5 is cooler still
- GSHTD Tmin is ~3 °C cooler than UrbClim; ERA5 Tmin is intermediate
- These are real differences in what each dataset represents: GSHTD is satellite-derived land surface temperature downscaled to 2m; UrbClim is a mesoscale urban climate model forced by ERA5; ERA5 is a global reanalysis that does not resolve urban morphology

**Practical consequence for the platform:** Any absolute-threshold metric (CDD20, CDD25, TR20, TR25) will produce different counts on different datasets because the datasets have different absolute temperature biases. Thresholds calibrated on GSHTD cannot be applied directly to ERA5 or UrbClim without bias correction. The recommended approach is to derive dataset-specific thresholds, or to use only relative metrics (e.g. percentile ranks within city) when comparing across datasets.

**Developer note:** ERA5 is a fallback for data acquisition only. It should not be used to derive CDD or EHF values that are then compared to GSHTD-derived values without explicit bias correction.

---

## 3. Exposure

### 3.1 The Person-Days Problem

The natural instinct for an exposure metric is to weight hazard by the number of people experiencing it: `exposure = heat_days × population`. This appears to capture both the intensity of heat and the number of people affected.

**Finding: at intra-urban scale (1 km), person-day rankings are population maps.**

| City / Metric | ρ(population rank, person-days rank) |
|---|---|
| Salvador — absolute heat days | +0.985 |
| Salvador — TX90p heat days | +0.966 |
| Teresina — absolute heat days | +1.000 |
| Teresina — TX90p heat days | +0.999 |
| Cáceres — absolute heat days | ~+0.99 |

**Why this happens — a CV argument:** When two variables with different CVs are multiplied, the product's rankings are dominated by the variable with the larger CV:

| Variable | CV (Salvador) |
|---|---|
| Population | 1.041 |
| TX90p heat days | 0.644 |
| Absolute heat days | 0.441 |

Population CV (1.04) is 1.6–2.4× larger than any heat metric CV. The high-population neighbourhood that has 50,000 people and average heat will almost always outrank the low-population neighbourhood that has 5,000 people and high heat, because the population ratio (10×) dominates the heat ratio (which is much smaller). The multiplication does not produce a genuinely bivariate metric — it produces a population map with small heat-induced perturbations.

**This holds at 100 m resolution (UrbClim):** ρ(pop, TX90p person-days) = +0.996. Person-days dominance is not a resolution artefact — it is structural, driven by the relative magnitudes of population and heat CV.

**Why it matters for the platform:**
- Person-days maps are visually compelling but analytically equivalent to population density maps at intra-urban scale
- Presenting person-days as a "heat exposure" metric misleads users into believing they are seeing heat burden when they are seeing population density
- The actual heat signal is buried in the noise of population variation

### 3.2 What Works Instead

**Population-weighted mean heat metric per neighbourhood:** Divide the neighbourhood total by the sum of population weights rather than multiplying. This preserves the spatial heat signal by showing the average heat experienced by a resident of each neighbourhood, without the domination problem.

**Quadrant classification (hot/cool × dense/sparse):** Rather than forcing a scalar product, classify each neighbourhood into one of four quadrants based on independent rankings of heat and population:

| Quadrant | Heat rank | Population rank | Interpretation | Priority |
|---|---|---|---|---|
| Hot + Dense | High | High | High absolute burden; maximum intervention impact | Immediate |
| Hot + Sparse | High | Low | Elevated per-person risk; fewer beneficiaries | Surveillance / early warning |
| Cool + Dense | Low | High | Large population, moderate risk | Baseline monitoring |
| Cool + Sparse | Low | Low | Lowest absolute burden | Lower priority |

This classification is more informative than any scalar composite because it exposes the two-dimensional structure of the prioritisation problem. It forces explicit decisions about whether "Hot + Sparse" is higher priority than "Cool + Dense" — which is a value judgement that should not be hidden inside a multiplication.

**For the hazard input to the composite risk score:** Use the population-weighted mean CDD25 (or EHF(Tmin) where CDD25 is not appropriate) per neighbourhood. Never multiply by population before this stage.

---

## 4. Vulnerability

### 4.1 Income (Brazilian Census 2022, Notebook 10)

Census-sector household head income (`renda_responsavel`, BRL) was aggregated to neighbourhood level for 22 Salvador neighbourhoods using area-weighted means from census sectors to administrative boundaries.

**Income has the highest spatial variation of any variable tested:**

| Variable | CV |
|---|---|
| Mean income (BRL) | 1.306 |
| Population | 1.041 |
| CDD25 heat metric | ~0.41 |
| TX90p heat days | 0.644 |
| Absolute heat days | 0.441 |

The income CV of 1.306 means that in any composite risk score combining hazard and income, income will structurally dominate rankings unless hazard is given an artificially high weight. This is not a flaw in the income data — it reflects genuine economic segregation in Brazilian cities. It is a fundamental constraint on any additive or multiplicative composite.

**Heat and income are spatially independent:**

| City | ρ(income, TX90p heat days) | p-value | Interpretation |
|---|---|---|---|
| Salvador | +0.13 | 0.59 | No significant correlation |
| Teresina | −0.07 | 0.51 | No significant correlation |
| Cáceres | −0.09 | 0.62 | No significant correlation |

The near-zero correlations are consistent with urban heat distribution being driven primarily by physical geography (coastal exposure, topography, urban morphology) rather than socioeconomic patterns. Wealthier neighbourhoods do not systematically experience less heat, nor do poorer neighbourhoods experience more, at this scale. This means heat and income are genuinely complementary risk dimensions — one does not predict the other, and both are needed for a complete risk picture.

**Income normalisation methods tested:**

| Method | Formula | Behaviour |
|---|---|---|
| Min-max | `1 − (x − min)/(max − min)` | Sensitive to outliers; high-income outliers compress the rest of the scale |
| Rank percentile | `(rank − 1)/(n − 1)` | Robust to outliers; uniform distribution of scores across neighbourhoods |

In practice, min-max normalisation can cause dramatic re-rankings when a single very high-income neighbourhood (e.g. a wealthy enclave) becomes the denominator for the entire scale. Rank percentile avoids this by treating each neighbourhood's relative position uniformly. **Rank percentile is the recommended default.**

**Composite rule matters:** ρ between additive and multiplicative composite risk scores = 0.68–0.84 across cities. These rules produce different neighbourhood rankings — the choice is not neutral. Multiplicative composites (hazard × vulnerability) give zero risk to any neighbourhood scoring zero on either dimension; additive composites preserve partial risk from a single high dimension. The choice should be explicit and documented in the platform, not treated as a default.

### 4.2 Alternative Vulnerability Proxies for Global Expansion

For the 49-city global expansion, Brazilian Census income is not available. The following proxies were evaluated (notebooks 10b, 10c):

| Proxy | Coverage | Resolution | Notes |
|---|---|---|---|
| Relative Wealth Index (Meta/Facebook) | ~93 LMICs | ~2.4 km | ML-derived from satellite, mobile, and survey data; best option for Global South |
| VIIRS Nighttime Lights (DNB) | Global | ~500 m | Proxy for economic activity; widely used; may saturate in dense commercial areas |
| GHSL Population Density | Global | 100 m | Available everywhere; reflects exposure volume rather than deprivation |
| WorldPop 100 m | Global | 100 m | Per-year; captures population dynamics; not a deprivation indicator |

**Developer recommendation:** Implement a pluggable vulnerability layer with three tiers: (1) Census income where available, (2) Relative Wealth Index for Global South LMICs, (3) VIIRS nighttime lights as a global fallback. The platform should make the active vulnerability layer explicit in the UI so users understand what proxy is being used.

---

## 5. Composite Risk Score

### 5.1 Combining Hazard and Vulnerability

The composite risk score combines a hazard layer (neighbourhood-level heat metric) with a vulnerability layer (neighbourhood-level socioeconomic indicator). Two composition rules were tested (notebook 11):

**Multiplicative:**
`risk = normalised_hazard × normalised_vulnerability`

**Additive (equal weights):**
`risk = 0.5 × normalised_hazard + 0.5 × normalised_vulnerability`

**Key observations:**

1. **The rules are not equivalent:** ρ between additive and multiplicative composites = 0.68–0.84. Different composition rules produce materially different neighbourhood rankings, and the difference affects who is prioritised for intervention.

2. **Vulnerability structurally dominates ranking in both rules:** Income CV (1.306) >> heat days CV (0.485 at best). In an equal-weight composite, the higher-CV variable (income) determines ranking for a majority of neighbourhoods. Giving heat and income equal weight in a formula does not give them equal influence over the output — that requires equalising their CVs first, which rank-percentile normalisation achieves.

3. **Rank percentile normalisation forces equal CV:** After rank-percentile normalisation, both hazard and vulnerability have uniform [0,1] distributions with equal variance, meaning the composition rule (additive vs multiplicative) genuinely determines the relative weight, rather than CV imbalance doing so implicitly.

**Recommended output format:** Quintile tiers within city (Very Low / Low / Moderate / High / Very High risk), not raw composite scores. Raw scores are not comparable across cities (they depend on each city's income and heat distributions), and small numerical differences are not meaningfully precise. Quintile tiers communicate relative priority clearly to non-technical users.

### 5.2 Regime-Specific Considerations

The appropriate hazard input to the composite depends on the city's climate regime. The updated recommendations incorporate the CDD25 findings from Section 2.1E:

| City type | Hazard discrimination (best metric) | Recommended hazard input | Risk score behaviour |
|---|---|---|---|
| Episodic / coastal (Salvador) | Good (CV ~0.46–0.49 for most metrics) | CDD25 or TX90p days; equivalent performance | Hazard contributes meaningfully to composite |
| Chronic interior (Teresina) | Poor for most metrics; good for CDD25 / TR25 | **CDD25** (CV 0.284, best performing) | Without CDD25, composite collapses to vulnerability map |
| Mixed diurnal / savanna (Cáceres) | Anti-correlated daytime/nighttime | **CDD25** for composite; keep TX90p and TN90p as separate layers | Daytime and nighttime risk are distinct phenomena; do not combine |

---

## 6. City Selection and Global Expansion (Notebook 00)

### 6.1 Sampling Framework

- 49 cities selected from GHSL-UCDB R2024 (11,422 global urban centres)
- Stratified by Köppen-Geiger climate zone (17 zones represented)
- 3 cities per zone, max 1 per country, with continent diversity enforced
- Population threshold: ≥ 500,000; bounding box ≤ 1.5° (excludes mega-agglomerations with complex multi-city administrative boundaries)
- Output: `data/city_selection.csv` with city name, country, GHSL UID, bounding box, Köppen zone

**Coverage implications:** The three Brazilian pilot cities represent Köppen zones Af (tropical rainforest / coastal), BSh (hot semi-arid), and Aw (tropical savanna). The global 49-city expansion introduces Am, Cfa, Cfb, Csa, Csb, BWh, BWk, and other zones. Metric performance at each climate regime is not yet characterised beyond the three pilot cities — the CDD25 findings may not generalise to, for example, temperate European cities (Cfb) where Tmin rarely exceeds 20 °C.

### 6.2 Technical Expansion Requirements

| Component | Current (Brazil) | Required for global |
|---|---|---|
| City registry | Hardcoded per-city dicts | Load from `city_selection.csv`; add Köppen field |
| GSHTD GEE paths | Latin America collection | Five regional collections; path lookup by bounding box |
| Admin boundaries | `geobr` (Brazil only) | `pygadm` / GADM for global coverage |
| Population | WorldPop with Brazil country filter | Remove country filter; handle projection per city |
| Vulnerability | Brazilian Census income | RWI (Global South) + VIIRS (global fallback) |
| Climate regime | Manually assigned | Derive from Köppen field; auto-select appropriate CDD threshold |
| CDD threshold | Fixed 20/25 °C (pilot) | Regime-dependent: 25 °C for tropical; 20 °C for subtropical; TBD for temperate |

---

## 7. Summary Recommendations for Platform Developers

### 7.1 Hazard Layer

| Recommendation | Rationale |
|---|---|
| **Implement CDD25 as primary hazard metric** | Outperforms EHF(Tmin) by 2–3× in chronic heat cities (Teresina CV 0.284, Cáceres CV 0.213); equivalent in episodic cities; simpler to compute and communicate |
| Also retain EHF(Tmin) for cities where CDD25 is near-zero | In cooler cities (Tmin rarely above 25 °C), CDD25 carries no signal; EHF(Tmin) remains the fallback |
| Also compute TX90p heat days | Standard ETCCDI metric; literature-comparable; required for interoperability with published climate indices |
| Store daytime (TX) and nighttime (TN) as separate layers | Anti-correlated in arid/savanna cities (Cáceres ρ = −0.45); averaging them loses information about distinct physical mechanisms |
| Use pixel-mean (population-weighted) hazard for neighbourhood aggregation | Person-days ≡ population density at intra-urban scale (ρ ≈ +0.99); never multiply before aggregating |
| Select CDD threshold based on climate regime | 25 °C for tropical cities; 20 °C for subtropical; evaluate saturation before committing |
| Expose CDD25 in °C·days/yr as the primary unit | Directly interpretable; no rank transformation required for communication (unlike EHF magnitude) |
| Flag 2017 and 2019 as climatological outliers in the UI | EHF values 8–11× the long-run mean in these years; users need context to avoid misinterpreting climatologies |

### 7.2 Exposure Layer

| Recommendation | Rationale |
|---|---|
| Do not use person-days as primary exposure metric | Rankings are population maps (ρ +0.97–1.00 with population at intra-urban scale) |
| Use quadrant classification (hot/cool × dense/sparse) as primary exposure view | Makes the two-dimensional prioritisation structure explicit; supports different intervention types |
| Population-weighted mean hazard per neighbourhood for scalar composite input | Preserves spatial heat signal; avoids domination by population count |
| Store population separately from heat metric; combine at query time | Preserves analytical flexibility; allows users to apply their own combination logic |

### 7.3 Vulnerability Layer

| Recommendation | Rationale |
|---|---|
| Implement pluggable vulnerability layer | Data availability differs by city and country; no single source is universally available |
| Use rank-percentile normalisation by default | Robust to income outliers; forces uniform variance so composition rule (not CV imbalance) determines weighting |
| Be explicit about additive vs multiplicative composite rule | Different rules produce materially different rankings (ρ 0.68–0.84 between them); not a neutral choice |
| Output quintile tiers within city, not raw scores | Prevents spurious cross-city comparison; communicates relative priority without false precision |

### 7.4 Architecture

| Recommendation | Rationale |
|---|---|
| Register climate regime (episodic / chronic / mixed diurnal) per city | Regime determines which CDD threshold is appropriate and whether TX/TN should be combined |
| Support multiple hazard metrics per city in data model | "Best metric" varies by regime; single-metric architecture will fail across the global expansion |
| Pre-compute CDD25 (and EHF fallback) to Zarr/NetCDF at city level | Offline pipeline before API; never live-compute CDD over 18-year records in production |
| Apply absolute-threshold metrics (CDD) only within a consistent dataset | CDD thresholds derived on GSHTD are not transferable to ERA5 or UrbClim without bias correction |
| ERA5 as data acquisition fallback only | ~9 km resolution; temperature biases differ from GSHTD; do not mix in the same threshold computation |

---

## 8. Open Questions

1. **CDD25 health validation:** CDD25 is the top-performing spatial metric, but its direct link to mortality or hospitalisation outcomes has not been established in the Brazilian or global literature. Before using as a primary public-facing metric, validation against health records (ideally DATASUS hospital admissions) should be conducted. EHF has Australian mortality validation; CDD25 does not yet have equivalent evidence.

2. **CDD threshold optimisation by climate regime:** The 20 °C and 25 °C thresholds were selected from literature. For temperate cities in the global expansion (Cfb, Cfa zones), Tmin may rarely exceed 25 °C, making CDD25 uninformative. A regime-specific threshold selection procedure is needed, potentially data-driven (e.g. select the threshold that maximises neighbourhood CV for each city's Tmin climatology).

3. **EHF(Tmin) acclimatisation window:** The 30-day window was calibrated on Australian temperate cities. In tropical cities where seasonal variation is smaller and heat is chronic, this window may be suboptimal. Sensitivity analysis varying the acclimatisation window length (15, 30, 60 days) has not been conducted for Teresina or Cáceres.

4. **Vulnerability combination rule:** Is multiplicative or additive risk composition appropriate for this platform? The choice shifts who is prioritised (multiplicative rewards joint extremes; additive is more inclusive of single-dimension risk). This is a value judgement requiring stakeholder input, not a purely technical decision.

5. **Temporal recency:** GSHTD ends 2020. The 2023–2024 global heat records and the accelerating tropical warming trend are not captured in the baseline. If the platform uses CDD25 thresholds calibrated on 2003–2020, they may underestimate current risk for recently warming cities.

6. **100 m resolution and CDD25:** The resolution analysis (Section 2.3) showed that absolute-threshold metrics benefit strongly from 100 m resolution (CV 0.44 → 0.82 for absolute heat days in Salvador). CDD25 uses an absolute threshold and would likely also benefit from 100 m Tmin data, but this has not been tested. UrbClim Tmin at 100 m has a ~3 °C warm bias relative to GSHTD that must be corrected before applying the same 25 °C threshold.

7. **Person-days at neighbourhood vs city scale:** The person-days dominance finding applies at intra-urban, 1 km scale. At the city-to-city scale, person-days are appropriate for comparing total heat burden across cities of different sizes (and are used in the global city-selection framework). The recommendation to avoid person-days applies specifically to intra-urban neighbourhood ranking.

8. **WorldPop temporal alignment:** Census boundaries (2010), WorldPop population data (year-matched 2003–2020), and income data (Brazilian Census 2022) have temporal misalignment. Population-weighted aggregations use 2020 WorldPop as the reference year; neighbourhoods with significant population change between 2010 and 2020 may have poorly matched boundaries and population grids.

---

*Notebooks: 00–16 | Primary data: GSHTD 1 km 2003–2020, WorldPop, Brazilian Census 2022, VITO UrbClim 100 m*
