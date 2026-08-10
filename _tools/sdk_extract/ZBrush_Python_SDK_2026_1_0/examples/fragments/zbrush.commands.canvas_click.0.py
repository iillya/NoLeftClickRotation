"""Code fragment for zbrush.commands.canvas_click.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Clicks at position (10, 10) in the canvas area.
zbc.canvas_click(10, 10)

# Clicks at position (10, 10) in the canvas area and then drags to (100, 100) and (200, 200).
zbc.canvas_click(10, 10, 100, 100, 200, 200)
