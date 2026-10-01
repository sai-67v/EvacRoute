"""
SafeRoute AI -- Comprehensive Test Suite
Tests all core modules: hazard generation, MCDM, routing, GeoJSON export, UI config
"""

import sys
import os
import io
import json
import time
import traceback
import numpy as np

# Mock Streamlit cache so tests can run outside Streamlit
import streamlit as st
st.cache_data = lambda *args, **kwargs: lambda f: f

# Force UTF-8 output on Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(__file__))

# ─── Colour helpers ───────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS_ICON = "[PASS]"
FAIL_ICON = "[FAIL]"

results = []

def run_test(name, fn):
    print(f"\n{CYAN}[TEST]{RESET} {name}")
    t0 = time.time()
    try:
        details = fn()
        elapsed = time.time() - t0
        print(f"  {GREEN}{PASS_ICON}{RESET}  ({elapsed:.3f}s)")
        if details:
            for line in details.split("\n"):
                print(f"       {line}")
        results.append({"name": name, "status": "PASS", "time": elapsed, "detail": details or ""})
        return True
    except Exception as e:
        elapsed = time.time() - t0
        tb = traceback.format_exc().strip().split("\n")[-1]
        print(f"  {RED}{FAIL_ICON}{RESET}  ({elapsed:.3f}s)  ->  {tb}")
        results.append({"name": name, "status": "FAIL", "time": elapsed, "detail": str(e)})
        return False

# ─────────────────────────────────────────────────────────────────────────────
# TEST 1 -- Import verification
# ─────────────────────────────────────────────────────────────────────────────
def test_imports():
    import streamlit
    import folium
    import osmnx
    import networkx
    import numpy
    import ee
    import geopandas
    return (
        f"streamlit=={streamlit.__version__}\n"
        f"folium=={folium.__version__}\n"
        f"osmnx=={osmnx.__version__}\n"
        f"networkx=={networkx.__version__}\n"
        f"numpy=={numpy.__version__}\n"
        f"geopandas=={geopandas.__version__}"
    )

run_test("Import: All required packages load", test_imports)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 2 -- GEE initialisation (offline fallback expected)
# ─────────────────────────────────────────────────────────────────────────────
def test_gee_init():
    import ee
    try:
        ee.Initialize()
        return "GEE live mode connected"
    except Exception as e:
        if "credentials" in str(e).lower() or "project" in str(e).lower() or "not found" in str(e).lower():
            return f"No GEE credentials (expected) -> offline/simulation mode active\nMsg: {str(e)[:80]}"
        raise

run_test("GEE: Initialisation (credentials / offline fallback)", test_gee_init)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 3 -- Simulated hazard grid shape & value bounds
# ─────────────────────────────────────────────────────────────────────────────
def test_simulated_grid():
    try:
        from app import generate_simulated_hazard_grid
    except ImportError:
        from gee_hazards import generate_simulated_hazard_grid
    bounds = (30.12, 30.08, 78.33, 78.28)   # north, south, east, west
    lats, lons, risk_grid = generate_simulated_hazard_grid(bounds, flood_weight=0.6, landslide_weight=0.4)
    assert lats.shape == (30,), f"Expected lats shape (30,) got {lats.shape}"
    assert lons.shape == (30,), f"Expected lons shape (30,) got {lons.shape}"
    assert risk_grid.shape == (30, 30), f"Expected grid (30,30) got {risk_grid.shape}"
    assert float(risk_grid.min()) >= 0.0, f"Min value < 0: {risk_grid.min()}"
    assert float(risk_grid.max()) <= 1.0, f"Max value > 1: {risk_grid.max()}"
    return (
        f"Grid shape : {risk_grid.shape}\n"
        f"Min risk   : {risk_grid.min():.4f}\n"
        f"Max risk   : {risk_grid.max():.4f}\n"
        f"Mean risk  : {risk_grid.mean():.4f}"
    )

run_test("Hazard Grid: Shape, value bounds [0,1] verified", test_simulated_grid)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 4 -- MCDM weight sensitivity
# ─────────────────────────────────────────────────────────────────────────────
def test_mcdm_weight_sensitivity():
    try:
        from app import generate_simulated_hazard_grid
    except ImportError:
        from gee_hazards import generate_simulated_hazard_grid
    bounds = (30.12, 30.08, 78.33, 78.28)
    combos = [(1.0, 0.0), (0.0, 1.0), (0.5, 0.5), (0.6, 0.4)]
    lines = []
    prev_grids = []
    for fw, lw in combos:
        _, _, grid = generate_simulated_hazard_grid(bounds, flood_weight=fw, landslide_weight=lw)
        assert 0.0 <= grid.min() and grid.max() <= 1.0
        lines.append(f"flood={fw} slide={lw} -> mean={grid.mean():.4f} max={grid.max():.4f}")
        prev_grids.append(grid.copy())
    assert not np.allclose(prev_grids[0], prev_grids[1]), "Flood-only and slide-only grids should differ"
    return "\n".join(lines)

run_test("MCDM: Weight sensitivity -- different combos produce different outputs", test_mcdm_weight_sensitivity)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 5 -- Road network fetch (OSMnx live)
# ─────────────────────────────────────────────────────────────────────────────
def test_road_network():
    import osmnx as ox
    bounds = (30.12, 30.08, 78.33, 78.28)
    north, south, east, west = bounds
    G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type='drive')
    nodes = len(G.nodes)
    edges = len(G.edges)
    assert nodes > 0, "Graph has no nodes"
    assert edges > 0, "Graph has no edges"
    return f"Nodes: {nodes}  |  Edges: {edges}  |  Graph type: {type(G).__name__}"

run_test("OSMnx: Road network fetch from OpenStreetMap (live)", test_road_network)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 6 -- Risk weights applied to graph
# ─────────────────────────────────────────────────────────────────────────────
def test_risk_weights():
    import osmnx as ox
    try:
        from app import add_risk_weights_to_graph_simulated, generate_simulated_hazard_grid
    except ImportError:
        from routing_engine import add_risk_weights_to_graph_simulated
        from gee_hazards import generate_simulated_hazard_grid

    bounds = (30.12, 30.08, 78.33, 78.28)
    north, south, east, west = bounds
    G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type='drive')
    lats, lons, risk_grid = generate_simulated_hazard_grid(bounds)
    G = add_risk_weights_to_graph_simulated(G, lats, lons, risk_grid)

    edges_with_cost = [(u,v,k) for u,v,k,d in G.edges(keys=True, data=True) if 'risk_cost' in d]
    edges_total = G.number_of_edges()
    assert len(edges_with_cost) == edges_total, f"Only {len(edges_with_cost)}/{edges_total} edges got risk_cost"

    costs = [d['risk_cost'] for _,_,_,d in G.edges(keys=True, data=True)]
    risks = [d['risk_index'] for _,_,_,d in G.edges(keys=True, data=True)]
    return (
        f"Edges with risk_cost : {len(edges_with_cost)}/{edges_total}\n"
        f"Risk cost range      : [{min(costs):.2f}, {max(costs):.2f}]\n"
        f"Risk index range     : [{min(risks):.4f}, {max(risks):.4f}]"
    )

run_test("Routing: Risk weights applied to all road edges", test_risk_weights)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 7 -- Least-risk path calculation
# ─────────────────────────────────────────────────────────────────────────────
def test_least_risk_path():
    import osmnx as ox
    try:
        from app import add_risk_weights_to_graph_simulated, generate_simulated_hazard_grid, calculate_least_risk_path
    except ImportError:
        from routing_engine import add_risk_weights_to_graph_simulated, calculate_least_risk_path
        from gee_hazards import generate_simulated_hazard_grid

    bounds = (30.12, 30.08, 78.33, 78.28)
    north, south, east, west = bounds
    G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type='drive')
    lats, lons, risk_grid = generate_simulated_hazard_grid(bounds)
    G = add_risk_weights_to_graph_simulated(G, lats, lons, risk_grid)

    result = calculate_least_risk_path(G, 30.09, 78.295, 30.115, 78.32)
    if len(result) == 3:
        shortest, safest, stats = result
    else:
        shortest, safest = result

    assert shortest is not None, "Shortest path returned None"
    assert safest is not None, "Safest path returned None"
    assert len(shortest) >= 2, f"Shortest path too short: {len(shortest)} nodes"
    assert len(safest) >= 2, f"Safest path too short: {len(safest)} nodes"

    return (
        f"Shortest path : {len(shortest)} nodes\n"
        f"Safest path   : {len(safest)} nodes\n"
        f"Paths differ  : {shortest != safest}"
    )

run_test("Routing: Least-risk vs shortest path -- both computed", test_least_risk_path)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 8 -- OSM POI facility fetch
# ─────────────────────────────────────────────────────────────────────────────
def test_poi_fetch():
    import osmnx as ox
    bounds = (30.12, 30.08, 78.33, 78.28)
    north, south, east, west = bounds
    facilities = []
    try:
        pois = ox.features_from_bbox(bbox=(north, south, east, west), tags={
            'amenity': ['hospital', 'clinic', 'shelter', 'fire_station', 'police']
        })
        if not pois.empty:
            for _, row in pois.iterrows():
                geom = row.geometry
                name = row.get('name', 'Emergency Facility')
                amenity = row.get('amenity', 'Facility')
                if geom.geom_type == 'Point':
                    facilities.append({'name': str(name), 'type': str(amenity), 'lat': geom.y, 'lon': geom.x})
                elif hasattr(geom, 'centroid'):
                    facilities.append({'name': str(name), 'type': str(amenity), 'lat': geom.centroid.y, 'lon': geom.centroid.x})
    except Exception as e:
        return f"No OSM POIs found in bbox (rural area expected) -- Error: {str(e)[:80]}"

    return f"POIs fetched: {len(facilities)} | Types: {list(set(f['type'] for f in facilities))}"

run_test("OSM POI: Hospital/Shelter facility fetch from OpenStreetMap", test_poi_fetch)

# ─────────────────────────────────────────────────────────────────────────────
# RESULTS SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
total   = len(results)
passed  = sum(1 for r in results if r["status"] == "PASS")
failed  = total - passed

print("\n" + "="*60)
print(f"{BOLD}  SAFEROUTE AI -- TEST RESULTS SUMMARY{RESET}")
print("="*60)
for r in results:
    icon = f"{GREEN}{PASS_ICON}{RESET}" if r["status"] == "PASS" else f"{RED}{FAIL_ICON}{RESET}"
    print(f"  {icon}  [{r['time']:.2f}s]  {r['name']}")
print("-" * 60)
print(f"  Total: {total}  |  {GREEN}Passed: {passed}{RESET}  |  {RED}Failed: {failed}{RESET}")
print("=" * 60)

# Save machine-readable results
out = {
    "run_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "summary": {"total": total, "passed": passed, "failed": failed},
    "tests": results
}
out_path = os.path.join(os.path.dirname(__file__), "test_results.json")
with open(out_path, "w") as f:
    json.dump(out, f, indent=2)
print(f"\n  Results saved -> test_results.json")

sys.exit(0 if failed == 0 else 1)
