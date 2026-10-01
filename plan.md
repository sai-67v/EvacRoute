# Project Plan: Geospatial Decision-Support System

> **Last Updated:** 2026-10-01 | **Status: ✅ ALL PHASES COMPLETE & FULLY VERIFIED**

## Challenge
Develop a geospatial decision-support system integrating multiple hazards and identify suitable emergency routes during disasters.

## Inputs Required
- Roads ✅ *(Fetched live from OpenStreetMap via OSMnx)*
- Flood/Landslide hazard data ✅ *(Derived from Copernicus GLO-30 DEM & JRC Surface Water via GEE)*
- Slope data ✅ *(Calculated via DEM slope modeling)*
- Settlements ✅ *(User-defined origin coordinate inputs)*
- Hospitals & Shelters ✅ *(Live OpenStreetMap POI extraction + user destination selector)*

---

## Tasks & Phases

### ✅ Phase 1: Data Preparation & Preprocessing — **COMPLETE**
1. ✅ Road network — fetched live via **OSMnx** from OpenStreetMap (`app.py`)
2. ✅ Flood hazard data — sourced from **JRC Global Surface Water** via Google Earth Engine (`gee_hazards.py` / `app.py`)
3. ✅ Slope/Landslide hazard — derived from **Copernicus GLO-30 DEM** via GEE (`gee_hazards.py` / `app.py`)
4. ✅ Simulated fallback grid available for instant offline/demo use (`app.py`)

---

### ✅ Phase 2: Risk Assessment & Hazard Mapping — **COMPLETE**
1. ✅ **Generate individual hazard layers** — slope (landslide proxy) & JRC water occurrence (flood)
2. ✅ **Normalize indicators** — slope ÷ 45°, JRC occurrence ÷ 100 → values clamped `[0, 1]`
3. ✅ **MCDM-based risk index** — weighted combination: `risk = (flood_w × flood_hazard + slide_w × landslide_hazard) / total_w`
4. ✅ **Identify high-risk locations** — MCDM risk index overlaid on roads; edge-level risk computed per road segment

---

### ✅ Phase 3: Emergency Routing — **COMPLETE**
1. ✅ **Routing Network** — road graph built from OSMnx `graph_from_bbox`
2. ✅ **Assign Risk Costs** — edge cost = `length × (1 + risk × 18)`, penalising high-hazard segments
3. ✅ **Least-Risk Route** — **Dijkstra** via NetworkX on `risk_cost` weight vs standard `length` weight — dual-path comparison: 🔵 Shortest vs 🔴 Safest

---

### ✅ Phase 4: Visualization & Web Application — **COMPLETE**
1. ✅ **Web app framework** — **Streamlit** with sidebar configuration
2. ✅ **Multi-hazard risk map** — rendered as **Folium HeatMap** (simulated) or **GEE TileLayer** (live)
3. ✅ **Interactive emergency-route map** — dual-path overlay with Start/End markers and layer control
4. ✅ **Export functionality** — GeoJSON download button for safest route (`app.py`)
5. ✅ **Hospital/Shelter point layers** — integrated as dedicated toggleable point layer group on the map (`app.py`)
6. ✅ **Risk level legend/colorbar** — styled colorbar explaining 🟢 Low, 🟡 Moderate, 🟠 High, and 🔴 Extreme risk levels

---

## Expected Outputs
- ✅ **Multi-hazard risk map + web visualization** — **100% Complete**
- ✅ **Interactive emergency-route map** — **100% Complete**
- ✅ **Exported GeoJSON route download** — **100% Complete**
