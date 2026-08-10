"""Code fragment for zbrush.commands.get_last_stroke.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Reapplies the last stroke.
stroke: zbc.Stroke = zbc.get_last_stroke()
zbc.canvas_stroke(stroke)
