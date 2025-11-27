import numpy as np
from scipy.spatial import cKDTree

def generate_shell_points(geometry, num_surface=5000, num_cut=5000, num_seeds=8):
    """
    Generates points only on the Surface and on the Voronoi Cut Planes.
    """
    # 1. Surface Points
    surface_points = geometry.surface_points(num_surface)
    
    # 2. Cut Points (on Voronoi Bisectors)
    print(f"Generating cut points...")
    
    bbox_min, bbox_max = geometry.get_bbox()
    seeds = []
    np.random.seed(42)
    while len(seeds) < num_seeds:
        pt = np.random.uniform(bbox_min, bbox_max)
        if geometry.contains(pt[None, :])[0]:
             seeds.append(pt)
    seeds = np.array(seeds)
    
    # Generate candidates for cuts
    candidates = np.random.uniform(bbox_min, bbox_max, (num_cut * 2, 3))
    mask = geometry.contains(candidates)
    candidates = candidates[mask]
    
    if len(candidates) > 0:
        cut_points = project_to_bisectors(candidates, seeds)
        
        # Filter points that ended up outside geometry
        mask_in = geometry.contains(cut_points)
        cut_points = cut_points[mask_in]
        
        if len(cut_points) > num_cut:
            cut_points = cut_points[:num_cut]
            
        points = np.vstack((surface_points, cut_points))
    else:
        points = surface_points
        
    print(f"Generated {len(points)} points")
    print(f"Seeds: {len(seeds)}")
    print(f"Surface points: {len(surface_points)}")
    print(f"Cut points: {len(cut_points)}")
    return points, seeds

def project_to_bisectors(candidates, seeds):
    """
    Projects candidate points to the nearest Voronoi bisector plane.
    """
    tree = cKDTree(seeds)
    dists, indices = tree.query(candidates, k=2)
    
    s1 = seeds[indices[:, 0]]
    s2 = seeds[indices[:, 1]]
    
    normals = s2 - s1
    midpoints = (s1 + s2) / 2
    
    norm_sq = np.sum(normals**2, axis=1)
    valid = norm_sq > 1e-8
    
    dot = np.sum((candidates - midpoints) * normals, axis=1)
    projections = candidates - (dot / norm_sq)[:, None] * normals
    
    return projections[valid]

