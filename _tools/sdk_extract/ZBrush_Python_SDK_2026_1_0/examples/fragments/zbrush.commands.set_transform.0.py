"""Code fragment for zbrush.commands.set_transform.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# To get a sense of the tool transform, we can set all values to their base values. Which will 
# leave us with a tiny tool in the upper left corner of the canvas. Which we would not be able
# to see unless we activate the transpose brush which indirectly indicates the position of the 
# tool.
position: tuple[float] = (0, 0, 0)
scale: tuple[float] = (1, 1, 1)
rotation: tuple[float] = (0, 0, 0)
zbc.set_transform(*position, *scale, *rotation)
zbc.press("Brush:Transpose")

# The position of a tool is set in canvas units in a y-up canvas coordinate system. Canvas system
# means that the width and height of the document canvas defines the bounds of the coordinate system
# and the world frame is aligned with the canvas plane. The z-position of a tool therefore acts
# mostly like a z-clipping plane and can usually be left at its default of 0. Natural scale (i.e.,
# 'zoom') values as present in user created tools usually lie around (100, 100, 100). The exact 
# values depend on how big or small the user dragged the tool when it was created. Rotation values 
# are expressed in degrees and are in relation to the canvas plane.

# Center the tool in the middle of the canvas, give it a uniform size of (100, 100, 100) and rotate 
# it so that we look along its y-axis (a top-down view).
canvas_width: float = zbc.get("Document:Width")
canvas_height: float = zbc.get("Document:Height")
position: tuple[float] = (canvas_width / 2, canvas_height / 2, 0)
scale: tuple[float] = (100, 100, 100)
rotation: tuple[float] = (0, 90, 90) 
zbc.set_transform(*position, *scale, *rotation)
