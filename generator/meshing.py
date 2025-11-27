import numpy as np
import SimpleITK as sitk
import trimesh
import vtk
from vtk.util import numpy_support
from scipy.spatial import cKDTree

def generate_labeled_volume(img, num_regions=8):
    """
    Generates a labeled volume by partitioning the input image mask
    using Voronoi seeds within the mask.
    """
    print("Generating labeled volume...")
    data = sitk.GetArrayFromImage(img)
    # data is (z, y, x)
    
    valid_z, valid_y, valid_x = np.where(data > 0)
    coords = np.column_stack((valid_z, valid_y, valid_x))
    
    if len(coords) == 0:
        return img
    
    n_points = len(coords)
    if n_points < num_regions:
        num_regions = n_points
        
    indices = np.random.choice(n_points, num_regions, replace=False)
    seeds = coords[indices]
    
    print(f"Partitioning {n_points} voxels into {num_regions} regions...")
    tree = cKDTree(seeds)
    _, labels = tree.query(coords)
    
    label_vol = np.zeros_like(data, dtype=np.int32)
    label_vol[valid_z, valid_y, valid_x] = labels + 1
    
    # Create SITK image
    label_img = sitk.GetImageFromArray(label_vol)
    label_img.CopyInformation(img)
    
    return label_img

def generate_meshes_from_labels(label_img):
    """
    Extracts surface meshes using VTK Discrete Marching Cubes.
    """
    print("Extracting meshes using VTK Discrete Marching Cubes...")
    
    arr = sitk.GetArrayFromImage(label_img)
    arr = arr.astype(np.int32)
    
    size = label_img.GetSize()
    spacing = label_img.GetSpacing()
    origin = label_img.GetOrigin()
    
    # Convert to VTK
    flat_data = arr.ravel() # Default C order
    vtk_data = numpy_support.numpy_to_vtk(num_array=flat_data, deep=True, array_type=vtk.VTK_INT)
    
    img_vtk = vtk.vtkImageData()
    img_vtk.SetDimensions(size)
    img_vtk.SetSpacing(spacing)
    img_vtk.SetOrigin(origin)
    img_vtk.GetPointData().SetScalars(vtk_data)
    
    # Discrete Marching Cubes
    dmc = vtk.vtkDiscreteMarchingCubes()
    dmc.SetInputData(img_vtk)
    dmc.GenerateValues(int(arr.max()), 1, int(arr.max()))
    dmc.Update()
    

    # Smoothing
    print("Smoothing with WindowedSinc...")
    smoother = vtk.vtkWindowedSincPolyDataFilter()
    smoother.SetInputConnection(dmc.GetOutputPort())
    smoother.SetNumberOfIterations(100)
    smoother.SetPassBand(0.025)
    smoother.NonManifoldSmoothingOn()
    smoother.NormalizeCoordinatesOn()
    smoother.Update()
    


    polydata = smoother.GetOutput()

    scene = trimesh.Scene()
    unique_labels = np.unique(arr)
    unique_labels = unique_labels[unique_labels != 0]
    
    print(f"Splitting {len(unique_labels)} regions...")
    
    # Check scalars
    scalars = polydata.GetPointData().GetScalars()
    assoc = vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS
    
    if not scalars:
        scalars = polydata.GetCellData().GetScalars()
        assoc = vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS
    
    if not scalars:
        print("Error: No scalars found after processing.")
        return scene
        
    scalar_name = scalars.GetName()

    for label in unique_labels:
        thresh = vtk.vtkThreshold()
        thresh.SetInputData(polydata)
        thresh.SetThresholdFunction(vtk.vtkThreshold.THRESHOLD_BETWEEN)
        thresh.SetLowerThreshold(label)
        thresh.SetUpperThreshold(label)
        thresh.SetInputArrayToProcess(0, 0, 0, assoc, scalar_name)
        thresh.Update()
        
        geo = vtk.vtkGeometryFilter()
        geo.SetInputConnection(thresh.GetOutputPort())
        geo.Update()
        
        output_poly = geo.GetOutput()
        
        if output_poly.GetNumberOfPoints() == 0:
            continue
            
        # Extract Vertices
        vtk_points = output_poly.GetPoints()
        if vtk_points is None: continue
        verts = numpy_support.vtk_to_numpy(vtk_points.GetData())
        
        # Extract Normals
        vtk_norms = output_poly.GetPointData().GetNormals()
        normals = None
        if vtk_norms:
            normals = numpy_support.vtk_to_numpy(vtk_norms)
        
        # Extract Triangles
        vtk_polys = output_poly.GetPolys()
        if vtk_polys is None: continue
        
        if vtk_polys.GetNumberOfCells() > 0:
            cells = numpy_support.vtk_to_numpy(vtk_polys.GetData())
            try:
                if cells[0] == 3:
                    faces = cells.reshape(-1, 4)[:, 1:]
                else:
                    raise ValueError("Non-triangle cells")
            except:
                faces = []
                vtk_polys.InitTraversal()
                id_list = vtk.vtkIdList()
                while vtk_polys.GetNextCell(id_list):
                    if id_list.GetNumberOfIds() == 3:
                        faces.append([id_list.GetId(0), id_list.GetId(1), id_list.GetId(2)])
                faces = np.array(faces)
        else:
            faces = np.zeros((0, 3))
            
        if len(faces) == 0: continue
        
        mesh = trimesh.Trimesh(vertices=verts, faces=faces)
        
        if normals is not None:
            mesh.vertex_normals = normals
        else:
            mesh.fix_normals()
        
        mesh.visual.face_colors = np.random.randint(0, 255, 4)
        mesh.visual.face_colors[:, 3] = 255
        
        scene.add_geometry(mesh, node_name=f"region_{label}")
        
    if scene.is_empty:
        print("Warning: Scene is empty!")
        scene.add_geometry(trimesh.creation.box(), node_name="dummy")
        
    return scene
