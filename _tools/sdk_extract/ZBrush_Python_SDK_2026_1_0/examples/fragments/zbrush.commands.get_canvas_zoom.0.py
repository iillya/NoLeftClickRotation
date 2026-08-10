"""Code fragment for zbrush.commands.get_canvas_zoom.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

result: float = zbc.get_canvas_zoom()
print(f"Canvas zoom: {result}")
