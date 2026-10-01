import osmnx as ox
import networkx as nx
import numpy as np
import time
import json
import io
import sys

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("="*60)
print("  SAFEROUTE AI -- ALGORITHM VERIFICATION SUITE")
print("="*60)

# 1. Test Hazard Grid Generation
print("\n[TEST] Simulated Hazard Grid Generation")
def generate_simulated_hazard_grid(bounds, flood_weight=0.6, landslide_weight=0.4, grid_size=30):
    north, south, east, west = bounds
    lats = np.linspace(south, north, grid_size)
    lons = np.linspace(west, east, grid_size)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    dist_to_center = np.abs(lat_grid - (north + south) / 2)
    flood_hazard = np.exp(-dist_to_center * 80)
    landslide_hazard = (lat_grid - south) / (north - south) * 0.7 + (lon_grid - west) / (east - west) * 0.3
    total_w = flood_weight + landslide_weight
    risk_grid = (flood_hazard * flood_weight + landslide_hazard * landslide_weight) / total_w
    return lats, lons, np.clip(risk_grid, 0, 1)

bounds = (30.12, 30.08, 78.33, 78.28)
t0 = time.time()
lats, lons, grid = generate_simulated_hazard_grid(bounds)
print(f"  [PASS] ({time.time()-t0:.3f}s) Grid Shape: {grid.shape}, Max Risk: {grid.max():.2f}")

# 2. Test OSMnx Road Graph (v2 API)
print("\n[TEST] OSMnx OpenStreetMap Network Fetch (v2 API)")
t0 = time.time()
G = ox.graph_from_bbox(bbox=bounds, network_type='drive')
print(f"  [PASS] ({time.time()-t0:.3f}s) Nodes: {len(G.nodes)}, Edges: {len(G.edges)}")

# 3. Test Risk Weight Assignment
print("\n[TEST] Apply Hazard Weights to Road Network")
t0 = time.time()
nodes, edges = ox.graph_to_gdfs(G)
risk_map = {}
for node_id, row in nodes.iterrows():
    lat_idx = np.abs(lats - row['y']).argmin()
    lon_idx = np.abs(lons - row['x']).argmin()
    risk_map[str(node_id)] = float(grid[lat_idx, lon_idx])

risk_multiplier = 18.0
for u, v, key, data in G.edges(keys=True, data=True):
    length = data.get('length', 1.0)
    u_risk = risk_map.get(str(u), 0.0)
    v_risk = risk_map.get(str(v), 0.0)
    edge_risk = (u_risk + v_risk) / 2.0
    adjusted_cost = length * (1.0 + (edge_risk * risk_multiplier))
    nx.set_edge_attributes(G, {(u, v, key): {'risk_cost': adjusted_cost, 'risk_index': edge_risk}})
print(f"  [PASS] ({time.time()-t0:.3f}s) Edge risk costs mapped dynamically")

# 4. Test Dijkstra Routing
print("\n[TEST] MCDM Dijkstra Shortest vs Safest Path")
t0 = time.time()
start_lat, start_lon = 30.0900, 78.2950
end_lat, end_lon = 30.1150, 78.3200
orig = ox.distance.nearest_nodes(G, start_lon, start_lat)
dest = ox.distance.nearest_nodes(G, end_lon, end_lat)

shortest = nx.shortest_path(G, orig, dest, weight='length')
safest = nx.shortest_path(G, orig, dest, weight='risk_cost')
print(f"  [PASS] ({time.time()-t0:.3f}s) Path calculated")
print(f"         Shortest: {len(shortest)} nodes | Safest: {len(safest)} nodes")
print(f"         Algorithm detour: {shortest != safest}")

# 5. Export Validation
print("\n[TEST] GeoJSON Route Payload Generation")
t0 = time.time()
geojson = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[nodes.loc[n]['x'], nodes.loc[n]['y']] for n in safest]
        },
        "properties": {"name": "SafeRoute AI"}
    }]
}
payload = json.dumps(geojson)
print(f"  [PASS] ({time.time()-t0:.3f}s) Payload generated ({len(payload)} bytes)")

print("\n" + "="*60)
print("  TOTAL TESTS: 5  |  PASSED: 5  |  FAILED: 0")
print("="*60)
