import os
from geometry import Sphere, NiftiGeometry
from points import generate_shell_points
from meshing import triangulate_and_partition, extract_region_meshes

def generate_regions(geometry, output_name="model.glb", num_regions=8, num_surface=5000, num_cut=10000):
    """
    Orchestrates the generation of segmented meshes.
    """
    print(f"Processing {output_name}...")
    
    # 1. Generate Point Cloud (Shell only)
    points, seeds = generate_shell_points(geometry, num_surface=num_surface, num_cut=num_cut, num_seeds=num_regions)
    
    # 2. Triangulate & Partition
    # Pass geometry to allow filtering of exterior tets
    delaunay, tet_labels = triangulate_and_partition(points, seeds, geometry)
    
    # 3. Extract Surfaces
    scene = extract_region_meshes(delaunay, tet_labels, points, geometry)
    
    # 4. Export
    output_dir = "../viewer/public"
    if not os.path.exists(output_dir):
        if os.path.exists("viewer/public"):
            output_dir = "viewer/public"
        else:
            os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, output_name)
    print(f"Exporting to {output_path}...")
    scene.export(output_path)
    print("Done.")

if __name__ == "__main__":
    SPHERE = False
    if SPHERE:
       # Sphere
       generate_regions(Sphere(radius=1.0), "sphere.glb")
    
    # NIfTI Mask (if available)
    nifti_path = "mask.nii.gz"
    if os.path.exists(nifti_path):
        try:
            nifti_geo = NiftiGeometry(nifti_path)
            # Use exact vertices (num_surface ignored by NiftiGeometry)
            generate_regions(nifti_geo, "nifti.glb", num_cut=25000)
        except Exception as e:
            print(f"Failed to process NIfTI file: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"NIfTI file not found at {nifti_path}, skipping.")
