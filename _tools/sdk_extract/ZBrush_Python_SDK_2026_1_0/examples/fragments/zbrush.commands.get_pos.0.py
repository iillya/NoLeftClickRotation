"""Code fragment for zbrush.commands.get_pos.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Returns the horizontal position of the 'Draw:Width' interface item in canvas coordinates.
pos_canvas: float = zbc.get_pos("Draw:Width", global_coordinates=False)
print(f"Canvas position: {pos_canvas}")

# Returns the horizontal position of the 'Draw:Width' interface item in global coordinates.
pos_global: float = zbc.get_pos("Draw:Width", global_coordinates=True)
print(f"Global position: {pos_global}")
