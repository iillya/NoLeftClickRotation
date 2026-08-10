"""Code fragment for zbrush.commands.get_mouse_pos.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Get the current mouse position in canvas space.
pos_canvas: tuple[float, float] = zbc.get_mouse_pos(global_coordinates=False)
print(f"Current mouse position in canvas space: {pos_canvas}")

# Get the current mouse position in global window space.
pos_global: tuple[float, float] = zbc.get_mouse_pos(global_coordinates=True)
print(f"Current mouse position in global window space: {pos_global}")
