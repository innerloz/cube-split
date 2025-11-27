import os
from geometry import Sphere, NiftiGeometry
from meshing import generate_labeled_volume, generate_meshes_from_labels

def generate_regions(geometry, output_name="model.glb", num_regions=8):
    """
    Orchestrates the generation of segmented meshes using voxel-based meshing.
    """
    print(f"Processing {output_name}...")
    
    # 1. Get Volumetric Representation
    print("Getting image volume...")
    img = geometry.get_image()
    
    # 2. Generate Labeled Volume (Voronoi partitioning on voxels)
    label_img = generate_labeled_volume(img, num_regions=num_regions)
    
    # 3. Extract Meshes using VTK
    scene = generate_meshes_from_labels(label_img)
    
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
       generate_regions(Sphere(radius=1.0), "sphere.glb", num_regions=8)
    
    # NIfTI Mask (if available)
    nifti_path = "mask.nii.gz"
    if os.path.exists(nifti_path):
        try:
            nifti_geo = NiftiGeometry(nifti_path)
            generate_regions(nifti_geo, "nifti.glb", num_regions=8)
        except Exception as e:
            print(f"Failed to process NIfTI file: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"NIfTI file not found at {nifti_path}, skipping.")
