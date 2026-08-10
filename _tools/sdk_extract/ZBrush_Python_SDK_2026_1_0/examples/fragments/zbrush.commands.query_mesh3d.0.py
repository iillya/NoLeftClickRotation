"""Code fragment for zbrush.commands.query_mesh3d.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

ID_POINT_COUNT: int = 0
ID_POLY_COUNT: int = 1
ID_BOUNDING_BOX: int = 2

# Almost all queries can fail. We for example only can get polygonal data when a mesh tool is 
# active and UV data only when the mesh has UVs.
try:
    pointCount: int = int(zbc.query_mesh3d(ID_POINT_COUNT)[0])
    polyCount: int = int(zbc.query_mesh3d(ID_POLY_COUNT)[0])
    bbox: tuple[float, float, float, float, float, float] = zbc.query_mesh3d(ID_BOUNDING_BOX, None)
except:
    raise RuntimeError("Could not access polygonal data. Active tool likely is not a mesh tool.")

# Calculate the size of the mesh and print the results.
x_neg, y_neg, z_neg, x_pos, y_pos, z_pos = bbox
dim_x: float = abs(x_pos - x_neg)
dim_y: float = abs(y_pos - y_neg)
dim_z: float = abs(z_pos - z_neg)

print(f"Active tool has {pointCount} points, {polyCount} polygons, and the dimensions x = "
      f" {dim_x}, y = {dim_y}, z = {dim_z}.")