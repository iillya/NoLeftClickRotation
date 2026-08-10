"""Code fragment for zbrush.commands.pixol_pick.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Get the center coordinate of the canvas and define the top left coordinate.
canvas_width: float = zbc.get("Document:Width")
canvas_height: float = zbc.get("Document:Height")
center_pos: tuple[float] = (canvas_width / 2, canvas_height / 2)
top_left_pos: tuple[float] = (0, 0)

# Get the hex color code for the top left position. Even when the canvas is seemingly empty, we will
# will always pick pixol information. We print the color, formatting it as a hex string. This will
# usually print 0x303030 because the top left corner is usually 'empty'.
color_int: int = int(zbc.pixol_pick(0, *top_left_pos))
print(f"Hex color at top left: {color_int:#0{8}X}")

# Get the color as RGB values. The converted hex components will be the same as the dedicated
# component values we query with pixol_pick().
r_c: int = (color_int >> 16) & 0xFF
g_c: int = (color_int >> 8) & 0xFF
b_c: int = color_int & 0xFF
r: float = zbc.pixol_pick(2, *top_left_pos)
g: float = zbc.pixol_pick(3, *top_left_pos)
b: float = zbc.pixol_pick(4, *top_left_pos)
print(f"RGB color at top left: ({r}, {g}, {b}) (converted from hex: {r_c}, {g_c}, {b_c})")

# Finally, get the pixol normal at the center of the screen.
normal: tuple[float] = (zbc.pixol_pick(6, *center_pos), 
                        zbc.pixol_pick(7, *center_pos), 
                        zbc.pixol_pick(8, *center_pos))
normal = tuple(map(lambda x: round(x, 3), normal))
print(f"Pixol normal at center: {normal}")
