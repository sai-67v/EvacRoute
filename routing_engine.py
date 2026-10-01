import osmnx as ox
import networkx as nx
import numpy as np

def get_road_network(roi_bounds):
    """
    Fetches the OpenStreetMap road network for a given bounding box.
    roi_bounds: tuple of (north, south, east, west)
    """
    north, south, east, west = roi_bounds
    G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type='drive')
    return G

def add_risk_weights_to_graph_gee(G, risk_image):
    """
    Assigns risk weights using Google Earth Engine reduceRegions.
    """
    import ee
    nodes, edges = ox.graph_to_gdfs(G)
    
    features = []
    MAX_NODES = 1500
    count = 0
    
    for node_id, row in nodes.iterrows():
        if count >= MAX_NODES:
            break
        lon, lat = row['x'], row['y']
        feat = ee.Feature(ee.Geometry.Point([lon, lat]), {'node_id': str(node_id)})
        features.append(feat)
        count += 1
        
    fc = ee.FeatureCollection(features)
    sampled = risk_image.reduceRegions(collection=fc, reducer=ee.Reducer.first(), scale=30)
    
    risk_map = {}
    try:
        results = sampled.getInfo()
        for feat in results.get('features', []):
            props = feat.get('properties', {})
            nid = props.get('node_id')
            for k, v in props.items():
                if k != 'node_id' and isinstance(v, (int, float)):
                    risk_map[nid] = float(v)
                    break
    except Exception as e:
        print("GEE bulk extraction notice:", e)

    return _apply_weights(G, risk_map)

def add_risk_weights_to_graph_simulated(G, lats, lons, risk_grid):
    """
    Fallback: assigns risk weights from simulated/interpolated hazard grid.
    """
    nodes, edges = ox.graph_to_gdfs(G)
    risk_map = {}
    
    for node_id, row in nodes.iterrows():
        lat, lon = row['y'], row['x']
        # Nearest grid point lookup
        lat_idx = np.abs(lats - lat).argmin()
        lon_idx = np.abs(lons - lon).argmin()
        risk_map[str(node_id)] = float(risk_grid[lat_idx, lon_idx])
        
    return _apply_weights(G, risk_map)

def _apply_weights(G, risk_map, risk_multiplier=12.0):
    for u, v, key, data in G.edges(keys=True, data=True):
        length = data.get('length', 1.0)
        u_risk = risk_map.get(str(u), 0.0)
        v_risk = risk_map.get(str(v), 0.0)
        edge_risk = (u_risk + v_risk) / 2.0
        
        # High-risk roads incur huge traversal penalties (diverting evacuation traffic)
        adjusted_cost = length * (1.0 + (edge_risk * risk_multiplier))
        nx.set_edge_attributes(G, {(u, v, key): {'risk_cost': adjusted_cost, 'risk_index': edge_risk}})
    return G

def calculate_least_risk_path(G, start_lat, start_lon, end_lat, end_lon):
    """
    Calculates the shortest distance route vs safest emergency route.
    """
    orig_node = ox.distance.nearest_nodes(G, start_lon, start_lat)
    dest_node = ox.distance.nearest_nodes(G, end_lon, end_lat)
    
    try:
        shortest_path = nx.shortest_path(G, orig_node, dest_node, weight='length')
        safest_path = nx.shortest_path(G, orig_node, dest_node, weight='risk_cost')
        return shortest_path, safest_path
    except Exception:
        return None, None
