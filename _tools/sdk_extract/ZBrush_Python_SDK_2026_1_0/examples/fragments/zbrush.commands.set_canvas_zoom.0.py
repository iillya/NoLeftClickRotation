"""Code fragment for zbrush.commands.set_canvas_zoom.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Set the canvas zoom to 2 (each Pixol is shown twice as large) and pan center of the the canvas to 
# the top left corner.
zbc.set_canvas_zoom(2)
zbc.set_canvas_pan(0, 0)


