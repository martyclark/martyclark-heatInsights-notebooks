# LCZ → Intervention Mapping: Review and Recommendations

**Date:** June 2026  
**Context:** Heat resilience intervention prioritisation for Salvador, Brazil (Amaralina neighbourhood pilot)  
**Method:** LCZ pixel counts extracted from GEE (`RUB/RUBCLIM/LCZ/global_lcz_map/latest`) joined to the *LCZ Actions Library (Final draft, April 2022)* and visualised as a Sankey diagram and cross-tabulation heatmap.

---

## What the visualisation revealed

The exercise of mapping the 46-action library onto LCZ pixel counts — and rendering the result as a Sankey diagram — was useful precisely because it exposed problems with the underlying mapping rather than confirming it. Three categories of issue emerged.

### 1. Actions that are not LCZ-specific have been mapped as if they are

A large share of the library consists of governance, policy, and informational actions whose applicability does not vary by urban morphology. Examples include:

- *Deploy a Heat Early Warning and Hydrometeorological Monitoring System* → mapped to LCZ 1, 2, 3, 5, 6
- *Establish Heat Hotlines for Emergency Assistance* → mapped to LCZ 1, 2, 3, 5, 6
- *Launch Training and Upskilling Programs for Heat-Resilient Jobs* → mapped to LCZ 8, 9, 10 only
- *Create a Financial Support Program for Extreme Weather Event Response* → mapped to LCZ 1, 2, 3, 5, 6

These assignments are arbitrary. A heat hotline is not more or less relevant because a neighbourhood is compact high-rise versus open low-rise. Forcing these actions through an LCZ filter gives them a spurious spatial rationale and distorts the ranking of genuinely place-specific interventions.

### 2. Physically-grounded actions have incomplete or incorrect LCZ assignments

Even among the actions that are legitimately LCZ-specific, the mapping contains gaps and errors:

| Action | Current mapping | Problem |
|---|---|---|
| Install Green Roofs | LCZ 5, 6 only | Compact types (1, 2, 3) have the highest building coverage and therefore the most roof area — a stronger case for green roofs |
| Install Public Shading Structures | LCZ 1, 2, 3 only | Open urban types (5, 6) have more pedestrian-scale public space and arguably greater need |
| Plant Street Trees | LCZ 5, 6, B, D | Compact low-rise (LCZ 3) is a primary candidate; absent from mapping |
| Launch Training & Upskilling | LCZ 8, 9, 10 only | Treated as a place-specific action when it is a workforce policy |

### 3. Two LCZ types are entirely absent from the library

**LCZ 4 (Open high-rise)** and **LCZ 7 (Lightweight low-rise)** have no actions assigned. LCZ 7 — which covers informal settlements and self-built housing — is particularly significant: it typically represents the highest-risk population from a heat vulnerability standpoint, yet the library offers no interventions targeted at this zone type.

---

## The fundamental distinction: neighbourhood-specific vs city-wide

The root cause of the mapping problems is that the library conflates two types of action that should be treated separately.

### Neighbourhood-specific interventions
Actions whose feasibility, effectiveness, and priority *vary with urban form*. They belong in a spatially differentiated analysis like this one. Examples:
- Cool / reflective roofs
- Green roofs and building insulation
- Street trees and urban greening
- Permeable and cool pavements
- Shading structures
- Parks and green-blue infrastructure
- Green roofs

Estimated count from the current library: **~15–18 actions**.

### City-wide interventions
Actions delivered at city scale whose spatial targeting is driven by *population vulnerability* or *institutional reach*, not by LCZ type. They should be assessed separately — for example, against heat risk indices or social vulnerability layers — rather than through an LCZ Sankey. Examples:
- Heat early warning and emergency response
- Community cooling centres
- Public awareness and education campaigns
- Wellness checks and heat hotlines
- Financial support programmes
- Occupational heat safety enforcement
- Training and upskilling programmes

Estimated count from the current library: **~28–30 actions**.

---

## Additional dimension: action type

Within the neighbourhood-specific group, a further distinction is operationally important:

| Type | Definition | Implication |
|---|---|---|
| **Retrofit** | Can be applied to the existing building stock or street fabric | Relevant for immediate programme design in any neighbourhood |
| **New build / redevelopment** | Only applicable when land turns over or buildings are replaced | Belongs in planning policy and developer guidance |
| **Open space** | Applies to streets, parks, and non-building land | Relevant to public works and parks budgets |

This distinction allows a city to ask: *"What can we do in Amaralina in the next three years?"* (retrofit and open space options) separately from *"What should we require in the next planning cycle?"* (new build standards).

---

## Recommendations

1. **Separate the library into two tiers** — neighbourhood-specific (spatially differentiated) and city-wide (vulnerability-differentiated) — and document the rationale for each assignment.

2. **Revise the LCZ mapping for the ~15–18 physical actions**, grounding each assignment in the physical characteristics of the LCZ (building coverage, height, surface materials, sky view factor) rather than assumed population density.

3. **Fill the LCZ 7 gap.** Lightweight low-rise / informal settlement zones require a dedicated set of actions (likely focusing on low-cost retrofit, shade, and community-level cooling) and should not remain unaddressed in the library.

4. **Add an action-type tag** (Retrofit / New build / Open space) to each neighbourhood-specific action so that outputs can be filtered by implementation scenario.

5. **Replace the binary LCZ mapping with a suitability weight** (0 = not applicable, 1 = applicable, 2 = particularly effective) to make the Sankey flow widths genuinely informative rather than a simple pixel-count proxy.

6. **Use the heatmap as a review tool.** The cross-tabulation (LCZ × intervention) is the most useful artefact for auditing and correcting the mapping — it makes gaps and asymmetries immediately visible in a way the action library spreadsheet does not.

---

## Files

| File | Description |
|---|---|
| `28_lcz_intervention_sankey.ipynb` | Notebook: GEE extraction, Sankey (flat and two-step), cross-tabulation heatmap |
| `heat_threshold_analysis/data/LCZ_Actions library _Final draft _April 22.csv` | Source action library — requires revision per recommendations above |
| `data/geobr_salvador_neighbourhoods_2010.gpkg` | Salvador neighbourhood boundaries used for pilot |
