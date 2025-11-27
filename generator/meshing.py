import numpy as np
from scipy.spatial import Delaunay, cKDTree
import trimesh

def triangulate_and_partition(points, seeds, geometry):
    """
    Performs Delaunay triangulation and partitions tetrahedra based on Voronoi seeds.
    Filters out tetrahedra that are outside the geometry.
    """
    print(f"Triangulating {len(points)} points...")
    delaunay = Delaunay(points)
    
    print("Partitioning regions...")
    tet_centroids = np.mean(points[delaunay.simplices], axis=1)
    
    # 1. Voronoi Partition
    tree = cKDTree(seeds)
    _, tet_labels = tree.query(tet_centroids)
    
    # 2. Geometry Filter
    # Mark tets outside the geometry as -1
    print("Filtering exterior tetrahedra...")
    is_inside = geometry.contains(tet_centroids)
    tet_labels[~is_inside] = -1
    
    print(f"Removed {np.sum(~is_inside)} exterior tetrahedra.")
    
    return delaunay, tet_labels

def extract_region_meshes(delaunay, tet_labels, points, geometry):
    """
    Extracts the boundary surfaces for each region using vectorized logic.
    """
    print("Extracting surfaces (vectorized)...")
    scene = trimesh.Scene()
    unique_labels = np.unique(tet_labels)
    
    # Filter out the -1 label (Exterior)
    unique_labels = unique_labels[unique_labels != -1]
    
    neighbors = delaunay.neighbors
    neighbor_indices = neighbors.copy()
    sentinel_idx = len(tet_labels)
    neighbor_indices[neighbors == -1] = sentinel_idx
    
    # Extend labels with "Outside" sentinel
    extended_labels = np.append(tet_labels, -1) 
    neighbor_labels = extended_labels[neighbor_indices]
    
    current_labels = tet_labels[:, np.newaxis]
    is_boundary_face = current_labels != neighbor_labels
    
    simplex_face_indices = np.array([[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]])
    
    for region_id in unique_labels:
        in_region = tet_labels == region_id
        region_boundary_mask = is_boundary_face[in_region]
        
        if not np.any(region_boundary_mask):
            continue
            
        region_tet_indices = np.where(in_region)[0]
        rows, cols = np.where(region_boundary_mask)
        global_tet_indices = region_tet_indices[rows]
        
        vertex_local_indices = simplex_face_indices[cols]
        target_simplices = delaunay.simplices[global_tet_indices]
        
        f0 = target_simplices[np.arange(len(rows)), vertex_local_indices[:, 0]]
        f1 = target_simplices[np.arange(len(rows)), vertex_local_indices[:, 1]]
        f2 = target_simplices[np.arange(len(rows)), vertex_local_indices[:, 2]]
        
        faces_global = np.stack((f0, f1, f2), axis=1)
        
        used_indices = np.unique(faces_global)
        index_map = np.full(len(points), -1, dtype=int)
        index_map[used_indices] = np.arange(len(used_indices))
        
        local_verts = points[used_indices]
        local_faces = index_map[faces_global]
        
        mesh = trimesh.Trimesh(vertices=local_verts, faces=local_faces)
        
        try:
            trimesh.repair.fix_normals(mesh)
        except:
            pass
            
        mesh.vertex_normals = geometry.compute_normals(mesh)
        scene.add_geometry(mesh, node_name=f"region_{region_id}")
        
    return scene
