# Algorithm Overview: Cube-Split Generator

This document outlines the algorithmic pipeline used in the `cube-split` project to generate segmented, watertight 3D meshes from volumetric data (NIfTI files or analytical shapes).

## High-Level Pipeline

The process follows a **Voxel-Based** workflow, leveraging `SimpleITK` for image processing and `VTK` for high-quality isosurface extraction and smoothing. This ensures that all generated regions fit together perfectly without gaps (watertight) and have smooth, organic boundaries.

The pipeline consists of four main stages:

1.  **Input Processing**: Loading the geometry or generating a rasterized volumetric mask.
2.  **Volumetric Partitioning**: Dividing the volume into distinct regions using Voronoi partitioning on the voxel grid.
3.  **Mesh Extraction**: converting each volumetric region into a smooth 3D mesh using Flying Edges and Windowed Sinc smoothing.
4.  **Scene Assembly**: Combining individual meshes into a single GLB scene for export.

---

## File & Function Reference

### 1. `geometry.py`

Handles the abstraction of input geometry. It standardizes different inputs (analytical spheres, medical images) into a common volumetric format (`SimpleITK.Image`).

#### Classes

*   **`Geometry` (Abstract Base Class)**
    *   Defines the interface for all geometry types.
    *   **Key Method**: `get_image()` - Must return a binary `SimpleITK.Image` representing the object mask.

*   **`Sphere`**
    *   Represents an analytical sphere.
    *   **`get_image()`**: Creates a 3D empty volume and rasterizes a sphere into it using numpy array operations ($x^2 + y^2 + z^2 \le r^2$). Returns the binary mask.

*   **`NiftiGeometry`**
    *   Handles loading of NIfTI (`.nii`, `.nii.gz`) medical imaging files.
    *   **`__init__(filepath)`**: Loads the file using `SimpleITK`, converts it to a boolean mask, and calculates bounding boxes.
    *   **`get_image()`**: Returns the loaded `SimpleITK` image object directly.

---

### 2. `meshing.py`

Contains the core algorithms for partitioning space and generating meshes.

#### Volumetric Partitioning
*   **`generate_labeled_volume(mask_img, num_regions)`**
    1.  Identifies all foreground voxel indices in the `mask_img`.
    2.  Selects `num_regions` random seed points from the foreground voxels.
    3.  Uses a **k-Dimensional Tree (`scipy.spatial.cKDTree`)** to perform a nearest-neighbor search for every foreground voxel against the seeds.
    4.  Assigns each voxel a label ($1 \dots N$) based on its nearest seed.
    5.  Returns a new `SimpleITK.Image` where pixel values represent Region IDs.

#### Mesh Generation
*   **`extract_surface_mesh(binary_vol, spacing, origin, direction, label_id)`**
    *   Generates a mesh for a single region.
    *   **Padding**: Pads the binary volume with 0s to ensure the mesh is closed (watertight) at the image boundaries.
    *   **Isosurface Extraction**: Uses **`vtkFlyingEdges3D`** (a faster, modern alternative to Marching Cubes) to generate a mesh at the 0.5 isosurface level.
    *   **Smoothing**: Applies **`vtkWindowedSincPolyDataFilter`**. This is a volume-preserving smoothing algorithm that removes "staircase" artifacts from the voxels without shrinking the mesh significantly.
    *   **Transform**: Maps the mesh vertices from Voxel Space back to Physical World Space using the image's Origin, Spacing, and Direction matrix.
    *   **Output**: Returns a `trimesh.Trimesh` object.

*   **`generate_meshes_from_labels(label_img)`**
    *   Iterates through every unique label found in the labeled volume.
    *   Extracts a binary mask for that specific label.
    *   Calls `extract_surface_mesh` for each label.
    *   Aggregates the resulting meshes into a `trimesh.Scene`.

#### Helpers
*   **`numpy_to_vtk_image(arr, spacing)`**: Converts numpy arrays into `vtkImageData` for VTK processing.
*   **`vtk_polydata_to_trimesh(polydata)`**: Converts VTK polydata structures into `trimesh` objects for easier export and manipulation.

---

### 3. `generate.py`

The entry point and orchestrator script.

#### Functions
*   **`generate_regions(geometry, output_name, num_regions)`**
    *   **Step 1**: Calls `geometry.get_image()` to get the voxel data.
    *   **Step 2**: Calls `meshing.generate_labeled_volume()` to partition the voxels.
    *   **Step 3**: Calls `meshing.generate_meshes_from_labels()` to create the 3D geometry.
    *   **Step 4**: Exports the final scene to a `.glb` file in the `viewer/public` directory.

*   **`__main__`**
    *   Configures whether to run on a generated Sphere or a local `mask.nii.gz` file.
    *   Initializes the appropriate `Geometry` subclass and runs the pipeline.

