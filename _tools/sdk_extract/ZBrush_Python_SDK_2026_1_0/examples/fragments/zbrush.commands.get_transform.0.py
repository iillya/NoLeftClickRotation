"""Code fragment for zbrush.commands.get_transform.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

data: list[float] = zbc.get_transform()
# The position of the tool in canvas space; its origin is the upper left corner.
print(f"Position: ({data[0]:.2f}, {data[1]:.2f}, {data[2]:.2f})")
# The scale of the tool in canvas space; to be able to see both (0, 0, 0) and (canvas_width, 
# canvas_height, 0) at the same time in the viewport, the scale must be (1, 1, 1). But common
# tool scales are more around (100, 100, 100).
print(f"Scale: ({data[3]:.2f}, {data[4]:.2f}, {data[5]:.2f})")
# The rotation of the tool. These are values in degree and not radians.
print(f"Rotation: ({data[6]:.2f}°, {data[7]:.2f}°, {data[8]:.2f}°)")
