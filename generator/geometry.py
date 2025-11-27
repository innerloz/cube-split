import numpy as np
import SimpleITK as sitk
import scipy.ndimage
from skimage import measure
import trimesh
import os

class Geometry:
    def get_image(self):
        raise NotImplementedError

class Sphere(Geometry):
    def __init__(self, radius=1.0):
        self.radius = radius
        
    def get_image(self):
        # Generate a voxel grid
        res = 128
        x = np.linspace(-1.2, 1.2, res)
        y = np.linspace(-1.2, 1.2, res)
        z = np.linspace(-1.2, 1.2, res)
        xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')
        
        dist = np.sqrt(xx**2 + yy**2 + zz**2)
        mask = (dist <= self.radius).astype(np.uint8)
        
        img = sitk.GetImageFromArray(mask)
        # Set spacing so physical size is correct (range 2.4 / 128)
        spacing = 2.4 / (res - 1)
        img.SetSpacing([spacing] * 3)
        img.SetOrigin([-1.2, -1.2, -1.2])
        return img

class NiftiGeometry(Geometry):
    def __init__(self, filepath):
        print(f"Loading NIfTI file from {filepath}...")
        self.image = sitk.ReadImage(filepath)
        
    def get_image(self):
        return self.image
