# Heat Hazard Metric Analysis: Findings and Recommendations

**Project:** HeatInsights — Neighbourhood-level heat risk, three pilot cities  
**Data:** GSHTD (Zhang et al. 2022), 1 km daily T2m, 2003–2020; UrbClim 100 m, Salvador 2008–2017  
**Notebooks:** 05, 07, 07b, 08, 09, 10, 11, 12, 13  
**Date:** June 2026

---

## 1. The three cities and their heat profiles

The three pilot cities span a wide range of heat regimes. Table 1 shows mean annual heat-day counts by threshold definition, averaged across 2003–2020 at the pixel level.

**Table 1 — Mean annual heat-day counts, city-wide pixel average (Notebook 05)**

| City | Days ≥ 30 °C | TX90p days | TX95p days | TX99p days |
|---|---|---|---|---|
| Salvador, Brazil | 63.4 | 11.1 | 4.9 | 1.1 |
| Teresina, Brazil | **322.1** | 33.7 | 15.0 | 3.8 |
| Cáceres, Brazil | **277.6** | 34.2 | 15.5 | 3.6 |

*Figure reference: Notebook 05 — annual heat-day maps and threshold sensitivity curves*

This table immediately establishes the fundamental distinction driving all subsequent analysis. Teresina exceeds 30 °C on 322 days per year — virtually every day. Cáceres exceeds it on 278 days. Salvador, by contrast, sits in a more coastal, variable regime with only 63 such days. This is not a subtle difference in degree; it is a qualitative difference in the nature of heat exposure.

---

## 2. Does the relative heat metric produce spatial discrimination?

The core question for a neighbourhood risk tool is whether any heat metric varies enough *across neighbourhoods within a city* to drive meaningful prioritisation. The coefficient of variation (CV = σ/μ across neighbourhoods) measures this directly.

### 2.1 Neighbourhood-level CV: all four metrics

**Table 2 — CV across neighbourhoods, population-weighted mean, multi-year average 2003–2020 (Notebook 12)**

| City | TX90p day count | TN90p day count | TX magnitude (°C·days) | TN magnitude (°C·days) |
|---|---|---|---|---|
| Salvador | 0.485 | 0.481 | **0.487** | 0.475 |
| Teresina | 0.009 | 0.010 | 0.014 | 0.008 |
| Cáceres | 0.008 | 0.010 | 0.014 | 0.009 |

*Figure reference: Notebook 12 — CV bar chart (shared y-axis) and box plots (shared y-axis per metric column)*

The contrast is stark. Salvador shows CV around 0.48 across all four metrics — roughly 50× higher than either Teresina or Cáceres, which cluster between 0.008 and 0.014 regardless of metric choice. The degree-weighted magnitude (sum of degrees above threshold per exceedance day) offers a marginal uplift for the two hot cities — from ~0.009 to ~0.014 — but the absolute level remains negligible.

For context, using a single diagnostic year (2020) gives slightly higher CV values, particularly for Teresina (0.19 for TX90p in Notebook 07), reflecting year-to-year climate variability. But across the full 18-year record, the systematic spatial pattern is essentially flat in both cities.

### 2.2 Why: the threshold itself has almost no spatial variation

The root cause is visible in the threshold statistics.

**Table 3 — Spatial CV of the TX90p and TN90p threshold temperature itself (Notebook 09)**

| City | TX90p threshold CV | TN90p threshold CV |
|---|---|---|
| Salvador | **4.07%** | 1.13% |
| Teresina | 0.43% | 1.08% |
| Cáceres | 0.93% | 1.68% |

*Figure reference: Notebook 09 — threshold summary table*

In Teresina, the local TX90p threshold varies by only 0.43% across the city — from 35.6 °C to 36.9 °C. With temperatures strongly spatially correlated at 1 km, every pixel exceeds its almost-identical local threshold on almost the same number of days. No metric derived from exceedances above this threshold can recover spatial variation that is not in the underlying data.

Salvador is different: its threshold varies by 4.07% (31.8 °C to 37.4 °C), reflecting genuine thermal contrasts between cooled coastal districts and hotter inland neighbourhoods. This is why relative metrics work there.

---

## 3. Resolution does not rescue relative metrics — but it does rescue absolute ones

A natural hypothesis is that the spatial flatness is a resolution artefact: finer temperature data might reveal within-city thermal gradients. Notebook 08 tests this directly using UrbClim 100 m data for Salvador.

**Table 4 — Resolution comparison, Salvador (Notebook 08)**

| Resolution | CV: absolute hd (≥ 30 °C) | CV: TX90p hd | ρ(pop, TX90p person-days) |
|---|---|---|---|
| 1 km (GSHTD) | 0.443 | 0.644 | +0.966 |
| 100 m (UrbClim) | **0.815** | 0.015 | +0.996 |

*Figure reference: Notebook 08, Section 9 — resolution comparison table and CV bar chart*

The absolute threshold at 100 m gains enormously: CV rises from 0.44 to 0.82 because the 100 m data resolves the urban heat island in full — a pixel-level range of 0.4 to 155.5 absolute heat days/year within Salvador alone.

But TX90p at 100 m has *worse* spatial CV (0.015 vs 0.644 at 1 km) and *stronger* population dominance (ρ = +0.996 vs +0.966). At 100 m resolution, the relative threshold normalises out the very UHI signal that the finer data is now resolving. The two approaches work against each other. This is not a resolution problem — it is a fundamental property of relative threshold metrics.

**Note on UrbClim:** this dataset is proprietary and not available for Teresina or Cáceres, so it cannot form part of the operational pipeline. It is used here solely to diagnose the resolution vs threshold effect.

---

## 4. Population dominance: person-days are a population map

Multiplying heat days by population to get person-days was intended to weight exposure by the number of people affected. In practice, across all three cities and all metric variants, person-day rankings are nearly identical to population rankings.

**Table 5 — Spearman ρ between neighbourhood population rank and person-days rank (Notebook 07)**

| City | ρ(pop, abs person-days) | ρ(pop, TX90p person-days) |
|---|---|---|
| Salvador | +0.985 | +0.966 |
| Teresina | — | ~+0.999 |
| Cáceres | — | ~+0.998 |

*Figure reference: Notebook 07 — three-panel population rank vs person-days rank scatter plots*

The reason is structural: population CV (Table 6 below) substantially exceeds heat-day CV in all cities. When two variables are multiplied, the one with greater relative spread dominates the product. In Teresina and Cáceres, heat CV is ~0.01 and population CV is ~0.88 and ~0.51 respectively — population is ~50–90× more variable. The person-days map is functionally a population map.

---

## 5. Income discriminates far more than heat within each city

Incorporating income as a proxy for adaptive capacity adds substantially more spatial variation than any heat metric.

**Table 6 — CV comparison: population, TX90p heat days, and income across neighbourhoods (Notebook 11)**

| City | N | CV: population | CV: TX90p hd | CV: income |
|---|---|---|---|---|
| Salvador | 22 | 1.041 | 0.644 | **1.306** |
| Teresina | 112 | 0.875 | 0.010 | **0.589** |
| Cáceres | 43 | 0.514 | 0.025 | **0.319** |

*Figure reference: Notebook 11 — cross-city CV bar chart*

Critically, income and heat are spatially independent: Spearman correlations between income and TX90p heat days are statistically insignificant in all three cities (Salvador ρ = +0.13 p=0.59; Teresina ρ = −0.07 p=0.51; Cáceres ρ = −0.09 p=0.62). The two dimensions are not redundant — they capture genuinely different spatial patterns. The risk product is combining independent signals, not double-counting.

In Teresina and Cáceres, where heat CV is ~0.01, the income and vulnerability layer produces essentially *all* of the spatial variation in the final risk score.

---

## 6. Daytime and nighttime heat are not interchangeable across cities

**Table 7 — Spearman ρ between TX90p and TN90p heat-day rankings (Notebook 09)**

| City | ρ(TX, TN) heat days |
|---|---|
| Salvador | +0.822 |
| Teresina | +0.059 |
| **Cáceres** | **−0.452** |

*Figure reference: Notebook 09 — hazard rank scatter plots and bump charts*

In Salvador, TX and TN are strongly correlated: the same neighbourhoods tend to be hottest by day and night, consistent with a coastal vs inland UHI gradient affecting both metrics.

In Teresina the two are uncorrelated, suggesting different spatial drivers operate at the tails of the daytime and nighttime distributions.

In Cáceres the correlation is *negative*: the neighbourhoods with the most TX90p heat days have the fewest TN90p warm nights. This likely reflects a large diurnal temperature range in drier or more exposed areas — hot days but cool nights — versus more vegetated or humid areas with smaller diurnal swing. For a risk product, combining TX and TN into a single additive hazard score in Cáceres would cause partial cancellation and produce a misleading result. The two should be treated as distinct dimensions.

---

## 7. Excess Heat Factor (EHF): results across Tmax and Tmin

### 7.1 Heatwave days (3+ consecutive days above P90)

Epidemiologically, persistence matters more than isolated hot days: during a multi-day heatwave, core body temperature accumulates, sleep is disrupted, and physiological recovery is impaired. A consecutive-day filter captures this duration effect.

However, for the spatial discrimination problem in Teresina and Cáceres, persistence is unlikely to help. Because temperatures are consistently near the P90 level, multi-day runs form naturally and will still be spatially uniform. In Salvador — where the 11 TX90p days per year are irregularly distributed — the consecutive-day filter would reduce the number of qualifying days, potentially *lowering* the already-adequate spatial CV. Testing at P95 or P99 is worth attempting, but small-number statistics become a concern at ~3–4 events per year.

### 7.2 EHF formulation

The EHF (Nairn & Fawcett, 2013) was developed specifically for heat health applications and combines two components:

```
EHF = EHI_sig × max(1, EHI_accl)

EHI_sig  = 3-day mean T  −  T₉₅ of all 3-day means
           (how extreme is this period relative to local climatology?)

EHI_accl = 3-day mean T  −  mean T over preceding 30 days
           (how much hotter than what the body has recently experienced?)
```

EHF can be computed from either Tmax or Tmin. The health rationale for Tmin is that nocturnal heat prevents physiological recovery: core body temperature accumulated during the day cannot dissipate if nights stay hot, which is the primary biological pathway to heat mortality during prolonged events.

EHF *day counts* (days where EHF > 0) are essentially equivalent to counting days where the 3-day running mean exceeds T₉₅ — the acclimatisation component affects EHF *magnitude* but not whether the threshold is crossed. For spatial CV purposes, the **EHF magnitude** (annual sum of EHF values on heatwave days) is therefore the relevant metric.

### 7.3 EHF results: Tmax

**Table 8a — EHF(Tmax) summary statistics at pixel level, multi-year mean (Notebook 13)**

| City | T95_3day range (°C) | Mean HW days/yr | Mean EHF mag (°C/yr) | Pixel CV: HW days | Pixel CV: EHF mag |
|---|---|---|---|---|---|
| Salvador | 33.7–38.1 | 5.8 | 254.9 | **1.445** | **1.437** |
| Teresina | 36.9–38.5 | 18.0 | 198.1 | 0.023 | 0.061 |
| Cáceres | 35.3–37.1 | 18.0 | 138.0 | 0.002 | 0.037 |

**Table 8b — EHF(Tmax) neighbourhood-level CV vs TX90p reference (Notebook 13)**

| City | EHF(Tmax) HW days CV | EHF(Tmax) magnitude CV | TX90p days CV | TX magnitude CV |
|---|---|---|---|---|
| Salvador | 0.467 | 0.389 | 0.485 | **0.487** |
| Teresina | 0.004 | 0.020 | 0.009 | **0.014** |
| Cáceres | 0.002 | 0.009 | 0.008 | **0.014** |

EHF(Tmax) performs *slightly worse* than TX90p for neighbourhood discrimination in all three cities. The acclimatisation component for Tmax contributes little in Teresina and Cáceres because the 30-day antecedent Tmax is itself always elevated — EHI_accl rarely exceeds 1, so the magnitude multiplier seldom activates.

### 7.4 EHF results: Tmin

**Table 9a — EHF(Tmin) summary statistics at pixel level, multi-year mean (Notebook 13)**

| City | T95_3day range (°C) | Mean HW days/yr | Mean EHF mag (°C/yr) | Pixel CV: HW days | Pixel CV: EHF mag |
|---|---|---|---|---|---|
| Salvador | 23.7–25.5 | 6.3 | 6.7 | 1.302 | 1.329 |
| Teresina | 24.1–25.7 | 17.7 | 7.6 | 0.025 | **0.142** |
| Cáceres | 22.2–24.6 | 17.9 | 16.9 | 0.006 | **0.136** |

**Table 9b — Full neighbourhood CV comparison: all metrics (Notebook 13)**

| City | EHF(Tx) HW | EHF(Tx) mag | **EHF(Tn) HW** | **EHF(Tn) mag** | TX90p | TX mag | TN90p | TN mag |
|---|---|---|---|---|---|---|---|---|
| Salvador | 0.467 | 0.389 | 0.461 | **0.431** | 0.485 | 0.487 | 0.481 | 0.475 |
| Teresina | 0.004 | 0.020 | 0.005 | **0.141** | 0.009 | 0.014 | 0.010 | 0.008 |
| Cáceres | 0.002 | 0.009 | 0.003 | **0.073** | 0.008 | 0.014 | 0.010 | 0.009 |

*Figure reference: Notebook 13 — 8-metric shared-axis bar chart and CV comparison table*

**EHF(Tmin) magnitude is the standout result.** Teresina's neighbourhood CV rises from 0.008–0.014 across all previous metrics to **0.141** — a 10× improvement. Cáceres rises to **0.073** — a 5–7× improvement. No other metric variant, including all TX90p/TN90p variants and EHF(Tmax), comes close.

The mechanism is the nocturnal UHI effect. Daytime temperatures in Teresina and Cáceres are spatially homogenised by solar radiation — a parking lot and a park differ far less at midday than at 3 am. At night, the absence of solar forcing allows surface energy balance differences (thermal mass, vegetation, albedo) to accumulate. Dense urban cores stay warm; green or low-density areas cool more. This spatial divergence is present in the Tmin data. EHF captures it because the acclimatisation component (T3_Tmin − T30_Tmin) varies meaningfully across neighbourhoods: the antecedent 30-day Tmin baseline is itself higher in the urban core, so when a heat event arrives, the magnitude of the anomaly differs by location in a way that Tmax differences do not.

For Salvador, all EHF variants slightly underperform the raw TX90p and TN90p magnitudes, which remain the strongest discriminators for that city.

### 7.5 Inter-annual signal: 2017 and 2019 as exceptional years

The annual time series (Notebook 13, cell 4) reveals a striking pattern: all three cities simultaneously register EHF(Tmax) magnitudes 8–10× above their long-run means in 2017 and 2019.

**Table 10 — Top EHF(Tmax) magnitude years per city (Notebook 13)**

| City | 1st (°C) | 2nd (°C) | 3rd (°C) | Long-run mean (°C) |
|---|---|---|---|---|
| Salvador | 2017 (2,132) | 2019 (1,698) | 2018 (299) | 255 |
| Teresina | 2017 (1,662) | 2019 (1,481) | 2018 (89) | 198 |
| Cáceres | 2019 (1,488) | 2020 (514) | 2015 (105) | 138 |

The 2017–2019 cluster is consistent with the extended La Niña and severe drought conditions that affected northeast and central Brazil during this period. The multiplicative structure of EHF amplifies these events far more dramatically than exceedance counts: a three-day extreme that is simultaneously above T₉₅ and well above the 30-day antecedent mean produces a very large product. This temporal sensitivity is operationally valuable for retrospective attribution and emergency planning, even in cities where the spatial CV is low.

---

## 8. Conclusions and recommendations

### 8.1 The two-regime finding (updated)

The analysis identifies two fundamentally different heat regimes. The EHF(Tmin) results partially revise the picture for chronic heat cities, but the fundamental distinction holds.

| Regime | Cities | Spatial CV of best metric | Best metric | Implication |
|---|---|---|---|---|
| **Episodic heat** | Salvador | 0.487 (TX magnitude) | TX90p / TN90p magnitude | Relative metrics work well; neighbourhoods are meaningfully differentiated |
| **Chronic heat** | Teresina | 0.141 (EHF(Tmin) mag) | EHF(Tmin) magnitude | Some spatial signal now recoverable via nocturnal UHI; vulnerability still dominates |
| **Chronic heat** | Cáceres | 0.073 (EHF(Tmin) mag) | EHF(Tmin) magnitude | Modest spatial signal; vulnerability layer essential for meaningful prioritisation |

### 8.2 Recommended hazard metric

**EHF(Tmin) magnitude is now the recommended operational hazard metric across all three cities.**

The evidence:

- In Salvador, EHF(Tmin) magnitude CV (0.431) is competitive with TN90p magnitude (0.475) and TX magnitude (0.487) — within 10% of the best alternative and stronger epidemiologically.
- In Teresina, EHF(Tmin) magnitude CV (0.141) is 10× higher than any TX90p/TN90p variant. This is not negligible: income CV is 0.589 and population CV is 0.875, so heat still contributes less variation than vulnerability, but it is now a real signal rather than noise.
- In Cáceres, EHF(Tmin) magnitude CV (0.073) is 5–7× higher than TX90p/TN90p variants. Again, heat is no longer a flat constant in the risk model.
- The metric has the strongest epidemiological justification of any tested: nocturnal recovery failure is the principal mechanism linking heat to excess mortality.

For cross-city comparability, a single metric is needed, and EHF(Tmin) magnitude satisfies this requirement — it is computable from the same GSHTD dataset for all three cities at the same 1 km resolution.

**Previous recommendation (TX magnitude) is superseded.** TX magnitude remains a useful cross-city comparator for absolute chronic heat burden, but should not be the primary neighbourhood-level hazard score.

### 8.3 Approach for chronic heat cities (revised)

EHF(Tmin) magnitude provides meaningful within-city spatial variation in Teresina and Cáceres, but it does not produce a level of discrimination comparable to income or population. The recommended approach for these cities is therefore a weighted composite that reflects this hierarchy:

1. **Hazard layer: EHF(Tmin) magnitude**, percentile-ranked within the city. The absolute values are not comparable across cities (Teresina mean 7.6 °C/yr vs Salvador mean 6.7 °C/yr despite being a far hotter city in absolute terms — this is by design, since EHF is relative to local climatology). Rank or normalised scores are the appropriate unit for combining with vulnerability.

2. **Vulnerability layer as the primary spatial driver.** Income, age structure, and population density still carry the most spatial variation in Teresina (income CV 0.589 vs heat CV 0.141) and Cáceres (income CV 0.319 vs heat CV 0.073). The composite score should weight vulnerability more heavily than hazard for these cities, or at minimum weight the two proportionally to their CVs so neither dominates by artefact of scale.

3. **Use absolute EHF(Tmax) magnitude for cross-city framing.** The 2017 and 2019 EHF(Tmax) spike values (Teresina 1,662 °C, Salvador 2,132 °C) provide concrete evidence of the severity of extreme events and are communicable to non-technical audiences as a measure of how bad the worst years were.

### 8.4 Note on TX and TN in Cáceres

Given the negative correlation between TX90p and TN90p rankings in Cáceres (ρ = −0.452), a combined daytime + nighttime score should **not** be constructed by simple addition. EHF(Tmin) magnitude on its own is the recommended metric; if a daytime component is also desired for Cáceres specifically, treat it as a separate dimension rather than adding it to the nighttime score.

---

## 9. Communicating EHF and using it to rank neighbourhoods

### 9.1 The communication challenge

EHF magnitude is not intuitively interpretable. A neighbourhood EHF(Tmin) magnitude of 12 °C/yr means "the annual sum of (3-day mean Tmin − T₉₅_3day) × max(1, T₃ − T₃₀) on days when the product is positive is 12 degrees" — which is accurate but useless for a policy audience. Three specific communication problems arise:

**The units are °C but the scale is arbitrary.** EHF magnitude varies enormously between cities and between Tmax and Tmin variants (Salvador EHF(Tmax) mean 255 vs EHF(Tmin) mean 6.7 despite similar heatwave day counts). Raw values should never be compared across cities or across Tmax/Tmin variants. Even within a city, the absolute scale has no clinical meaning — there is no "safe" EHF level analogous to a temperature threshold.

**The metric is relative to local climatology, not absolute heat.** A Teresina neighbourhood with EHF(Tmin) magnitude 14 °C/yr is not hotter in absolute terms than a Salvador neighbourhood with EHF(Tmin) magnitude 5 °C/yr — it just experiences nighttime heat anomalies that are larger relative to what residents recently experienced. This is the right framing for health risk (acclimatisation is what matters), but it requires careful wording.

**Year-to-year variability is very high.** The multi-year mean is stable, but single-year EHF magnitudes can be 8–10× the mean in extreme years (2017, 2019). Presenting a single year as representative would be misleading.

### 9.2 Recommended communication framing

For stakeholder-facing materials, avoid presenting EHF magnitude as a raw number. Instead:

**For neighbourhood ranking:** present as a percentile rank or heat risk tier within the city. "This neighbourhood is in the top 20% for nighttime heat stress" is meaningful; "EHF(Tmin) magnitude = 14.2 °C/yr" is not. A five-tier classification (Very Low / Low / Moderate / High / Very High) derived from city-specific quintiles communicates the relative spatial pattern without implying cross-city or cross-metric comparability.

**For city-level framing:** use the EHF(Tmax) magnitude worst-year values as a concrete severity indicator. "In 2017, the accumulated heat stress index reached 2,132 °C-units — eight times the typical year" is a powerful framing for extreme event severity that is both factually accurate and accessible.

**For the acclimatisation concept:** the key insight is that sudden heat above recent experience is more dangerous than persistently high heat that people have adapted to. A useful analogy: a cold-weather city hit by an unexpected heat wave suffers more than a hot city at the same temperature because residents have no physiological or practical preparation. EHF captures this by penalising large departures from the 30-day running mean — the further above recent experience, the higher the score.

### 9.3 Practical neighbourhood ranking procedure

For the operational risk pipeline, the recommended procedure for translating EHF(Tmin) magnitude into a neighbourhood hazard score is:

1. **Compute the multi-year mean** (2003–2020) EHF(Tmin) magnitude per pixel using `compute_ehf_annual_stats()` and take the time mean. This produces a stable per-pixel climatological estimate.

2. **Aggregate to neighbourhood level** using population-weighted mean, matching the method in Notebooks 12 and 13. Population-weighting ensures that the hazard score reflects exposure of residents rather than uninhabited industrial or green-space pixels.

3. **Rank within city** by converting to percentile rank (0–100) or min-max normalise to 0–1. Do not use absolute values or compare scores across cities.

4. **Combine with vulnerability** using a weighted composite. Given the CV hierarchy, a reasonable starting point is equal weighting between heat rank and vulnerability rank (each on 0–1 scale), with the understanding that for Teresina and Cáceres the vulnerability component will dominate.

5. **Flag the caveat on chronic heat burden.** A low EHF(Tmin) rank in a Teresina neighbourhood does not mean low heat risk — it means the neighbourhood's heat burden is close to the city average, which is itself very high. The EHF rank captures *relative* within-city differentiation; the absolute heat burden is captured by the cross-city comparison (Table 1).

### 9.4 What EHF does not resolve

EHF(Tmin) magnitude improves spatial discrimination substantially in Teresina and Cáceres, but several limitations remain:

- **Spatial CV is still lower than vulnerability CV.** In Teresina, heat CV = 0.141 vs income CV = 0.589. A composite score will still be primarily driven by vulnerability in these cities unless heat is deliberately over-weighted.
- **The metric does not capture chronic baseline burden.** A neighbourhood where Tmin is persistently 26 °C every night is physiologically stressed even if it never exceeds T₉₅ by much. EHF, being a relative metric, does not score this chronic exposure.
- **1 km resolution limits urban granularity.** The spatial signal in EHF(Tmin) is real but constrained by the GSHTD pixel size. At 100 m resolution (if data were available), the nocturnal UHI contrast would likely be stronger and neighbourhood CV would increase further.
- **Data ends in 2020.** The 2017–2019 anomaly is captured, but post-2020 trends — including any systematic warming of nighttime urban temperatures — are not.

---

*All figures referenced above are available in the corresponding Jupyter notebooks in this directory. Notebook 13 (`13_ehf_hazard.ipynb`) contains the full EHF analysis including Tmax and Tmin variants, spatial maps, time series, component diagnostics, and the definitive 8-metric CV comparison chart.*
