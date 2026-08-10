"""Code fragment for zbrush.commands.set_canvas_pan.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Centers a 640x480 canvas in the document view, i.e., the visible area of the canvas. This only has an
# effect when the canvas is larger than the document view.
result: tuple[float, float] = zbc.set_canvas_pan(320, 240)