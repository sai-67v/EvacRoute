import ee
import numpy as np

def initialize_ee(project=None):
    """
    Initializes Google Earth Engine with optional project ID and fallback.
    """
    try:
        if project and project.strip():
            ee.Initialize(project=project.strip())
        else:
            ee.Initialize()
        return True, "Google Earth Engine initialized successfully."
    except Exception as e:
        return False, str(e)

def get_mcdm_risk_index(roi, flood_weight, landslide_weight, elevation_cutoff=2000):
    """
    Computes a Multi-Criteria Decision Making (MCDM) risk index using Google Earth Engine.
    """
    dem = ee.Image('COPERNICUS/DEM/GLO30').select('DEM')
    slope = ee.Terrain.slope(dem)
    
    # 1. Landslide hazard from slope
    landslide_hazard = slope.divide(45.0).clamp(0, 1)
    
    # 2. Flood hazard from JRC surface water + flat areas
    jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
    water_occurrence = jrc.select('occurrence').unmask(0)
    flood_hazard_history = water_occurrence.divide(100.0)
    
    flat_hazard = ee.Image(1.0).subtract(slope.divide(5.0)).clamp(0, 1)
    elevation_mask = dem.lt(elevation_cutoff)
    
    flood_hazard = flood_hazard_history.add(flat_hazard).divide(2.0).updateMask(elevation_mask).unmask(0)
    
    # 3. Weighted MCDM overlay
    total_weight = flood_weight + landslide_weight
    if total_weight == 0:
        total_weight = 1.0
        
    weighted_flood = flood_hazard.multiply(flood_weight)
    weighted_landslide = landslide_hazard.multiply(landslide_weight)
    mcdm_risk = weighted_flood.add(weighted_landslide).divide(total_weight)
    
    return mcdm_risk.clip(roi)

def generate_simulated_hazard_grid(bounds, flood_weight=0.5, landslide_weight=0.5, grid_size=30):
    """
    Fallback hazard generator when Earth Engine credentials/project are unavailable.
    Generates a realistic multi-hazard gradient (flood basin in the center/river + steep slopes in edges).
    """
    north, south, east, west = bounds
    lats = np.linspace(south, north, grid_size)
    lons = np.linspace(west, east, grid_size)
    
    # Create synthetic elevation and water proximity
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    # River / valley in center-west to center-east
    dist_to_center = np.abs(lat_grid - (north + south) / 2)
    flood_hazard = np.exp(-dist_to_center * 80)
    
    # Slopes higher in the north-east
    landslide_hazard = (lat_grid - south) / (north - south) * 0.7 + (lon_grid - west) / (east - west) * 0.3
    
    total_w = flood_weight + landslide_weight
    if total_w == 0:
        total_w = 1.0
        
    risk_grid = (flood_hazard * flood_weight + landslide_hazard * landslide_weight) / total_w
    risk_grid = np.clip(risk_grid, 0, 1)
    
    return lats, lons, risk_grid
