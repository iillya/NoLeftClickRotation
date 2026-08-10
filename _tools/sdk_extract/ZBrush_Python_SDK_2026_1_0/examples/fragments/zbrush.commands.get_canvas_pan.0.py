"""Code fragment for zbrush.commands.get_canvas_pan.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

result: tuple[float, float] = zbc.get_canvas_pan()
print(f"Canvas pan: {result}")
