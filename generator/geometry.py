import numpy as np
import SimpleITK as sitk
import scipy.ndimage
from skimage import measure
import trimesh
import os

class Geometry:
    def contains(self, points):
        raise NotImplementedError
    
    def surface_points(self, count):
        raise NotImplementedError
        
    def project_to_surface(self, points):
        raise NotImplementedError

    def get_bbox(self):
        raise NotImplementedError
    
    def compute_normals(self, mesh):
        raise NotImplementedError

class Sphere(Geometry):
    def __init__(self, radius=1.0):
        self.radius = radius
        
    def contains(self, points):
        return np.linalg.norm(points, axis=1) < self.radius

    def surface_points(self, count):
        # Fibonacci Sphere
        golden_ratio = (1 + 5**0.5) / 2
        i = np.arange(0, count)
        theta = 2 * np.pi * i / golden_ratio
        phi = np.arccos(1 - 2 * (i + 0.5) / count)
        
        x = self.radius * np.sin(phi) * np.cos(theta)
        y = self.radius * np.sin(phi) * np.sin(theta)
        z = self.radius * np.cos(phi)
        return np.stack((x, y, z), axis=-1)

    def project_to_surface(self, points):
        dists = np.linalg.norm(points, axis=1)
        return points / dists[:, None] * self.radius

    def get_bbox(self):
        return [(-self.radius, -self.radius, -self.radius), (self.radius, self.radius, self.radius)]
    
    def compute_normals(self, mesh):
        vertex_normals = mesh.vertex_normals.copy()
        dists = np.linalg.norm(mesh.vertices, axis=1)
        is_surface = np.abs(dists - self.radius) < 0.05
        if np.any(is_surface):
            vertex_normals[is_surface] = mesh.vertices[is_surface] / dists[is_surface, np.newaxis]
        norms = np.linalg.norm(vertex_normals, axis=1)
        vertex_normals[norms > 0] /= norms[norms > 0][:, np.newaxis]
        return vertex_normals

class NiftiGeometry(Geometry):
    def __init__(self, filepath):
        print(f"Loading NIfTI file from {filepath}...")
        image = sitk.ReadImage(filepath)
        
        # Convert to numpy array (z, y, x)
        self.data = sitk.GetArrayFromImage(image)
        self.origin = np.array(image.GetOrigin())
        self.spacing = np.array(image.GetSpacing())
        self.direction = np.array(image.GetDirection()).reshape(3, 3)
        
        # Assuming binary mask > 0 is ROI
        self.data = (self.data > 0).astype(bool)
        
        # Calculate transforms
        try:
            self.inv_direction = np.linalg.inv(self.direction)
        except:
            self.inv_direction = np.eye(3)
            
        # Compute BBox
        z, y, x = np.where(self.data)
        min_idx = np.array([x.min(), y.min(), z.min()])
        max_idx = np.array([x.max(), y.max(), z.max()]) + 1
        
        p1 = self._idx_to_world(min_idx)
        p2 = self._idx_to_world(max_idx)
        self.bbox_min = np.minimum(p1, p2)
        self.bbox_max = np.maximum(p1, p2)
        
        # Extract surface mesh
        self.mesh = self._extract_surface_mesh()
        
        # Debug: save mesh
        debug_dir = "debug"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir, exist_ok=True)
        try:
            # Save as GLB (robust)
            self.mesh.export(os.path.join(debug_dir, "surface_mesh.glb"))
        except Exception as e:
            print(f"Could not save debug mesh: {e}")

    def _idx_to_world(self, idx):
        # idx is (N, 3) x, y, z
        scaled = idx * self.spacing
        return self.origin + (self.direction @ scaled.T).T

    def _world_to_idx(self, points):
        # Returns (N, 3) x, y, z float indices
        diff = points - self.origin
        scaled = (self.inv_direction @ diff.T).T
        idx = scaled / self.spacing
        return idx

    def _extract_surface_mesh(self):
        # Marching cubes on (z, y, x) data
        # Returns verts in (row, col, slice) -> (z, y, x)
        verts, faces, normals, values = measure.marching_cubes(self.data, level=0.5)
        
        # Convert verts to (x, y, z)
        verts_xyz = verts[:, ::-1]
        
        # Transform to world space
        world_verts = self._idx_to_world(verts_xyz)
        
        return trimesh.Trimesh(vertices=world_verts, faces=faces, vertex_normals=normals)

    def contains(self, points):
        # Robust check using linear interpolation
        idx = self._world_to_idx(points)
        # Map coordinates expects (z, y, x)
        coords = [idx[:, 2], idx[:, 1], idx[:, 0]]
        
        # Sample the boolean volume (0.0 to 1.0)
        values = scipy.ndimage.map_coordinates(self.data.astype(float), coords, order=1, mode='constant', cval=0.0)
        
        # Threshold at 0.5 (isosurface level)
        return values > 0.5

    def surface_points(self, count):
        # Return exact vertices from the high-quality marching cubes mesh
        # Ignoring 'count' to preserve exact geometry
        print(f"Using {len(self.mesh.vertices)} exact surface vertices.")
        return self.mesh.vertices

    def project_to_surface(self, points):
        nearest, _, _ = self.mesh.nearest.on_surface(points)
        return nearest

    def get_bbox(self):
        return [self.bbox_min, self.bbox_max]
    
    def compute_normals(self, mesh):
        # For NIfTI, trust the mesh normals (calculated by trimesh/marching cubes)
        # They are usually good. Recomputing might lose sharpness if not careful.
        return mesh.vertex_normals
